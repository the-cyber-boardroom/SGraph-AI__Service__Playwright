---
title: "Generic sg aws auth resolution + transparent least-privilege AssumeRole — with `sg el lets cf iam` as the case study"
version: v0.2.40
date: 2026-05-21
status: PLAN — not yet implemented. Why / What / How for review before any code lands.
audience: next agent on the sg aws credential layer + the operator (dinis)
related:
  - sgraph_ai_service_playwright__cli/credentials/service/Sg__Aws__Session.py        # the existing chokepoint
  - sg_compute_specs/vault_publish/setup/service/Setup__IAM.py                        # the transparent iam-admin assume pattern to generalise
  - sgraph_ai_service_playwright__cli/aws/iam/service/IAM__AWS__Client.py
  - library/guides/v0.2.31__setup_cli_pattern.md                                      # the CRUD/verbs/drift pattern the iam commands follow
  - library/guides/v0.2.39__tui_cli_separation.md
---

# Generic AWS auth resolution + least-privilege AssumeRole

> **Goal.** No `sg aws *` command should ever dump a raw `NoCredentialsError` traceback.
> When auth is missing or insufficient, the command should *help the user fix it* —
> pick a stored credential, or transparently assume a **least-privilege role scoped to
> exactly that command family**. We build the machinery **generic** (it will be used
> across every `sg aws *` section) and prove it on `sg el lets cf *` first, including a
> `sg el lets cf iam` CRUD that creates and maintains the family's custom role.
>
> **The generic auth layer is the primary deliverable.** `sg el lets cf` is the first of
> ~12 `sg aws *` sections (s3, ec2, ecr, cf, logs, firehose, fargate, cloudtrail, alb,
> bedrock, iam, …). Onboarding each subsequent section must cost only a small,
> declarative **registry entry + one decorator on its commands** — never new auth code.
> If a second section needs us to write logic again, the abstraction is wrong.

*(Note on naming: the operator calls it "sg lets cf"; the real path is `sg el lets cf …`
— `el` = elastic → `lets` → `cf`. This plan uses the real path.)*

---

## 1. Why

1. **The failure mode is ugly and unhelpful.** `sp el lets cf tui sync` with no creds
   throws `botocore ... NoCredentialsError` as a stack trace. The user is left to guess
   what to do. Every `sg aws *` command can hit this.
2. **We already have the pieces but they are not joined up.** The credential keyring,
   the STS-AssumeRole session, the "current role" context, and a *transparent assume*
   pattern (`iam-admin`) all exist — but only half the AWS clients flow through them,
   and there is no shared error-recovery UX.
3. **Least privilege is currently all-or-nothing.** Commands run with whatever broad
   creds the operator has. A per-family role (assumed transparently) is a large,
   cheap security win — even a coarse "everything `sg el lets cf` needs and nothing
   else" role beats running as admin.
4. **This must be reusable everywhere.** The same workflow — *resolve auth → on failure,
   offer choices → transparently assume the family's least-priv role* — applies to
   `sg aws s3`, `sg aws ec2`, `sg aws firehose`, `sg aws logs`, every section. So we
   design it generic and instantiate per family; `sg el lets cf` is the case study.

---

## 2. What exists today (grounded)

| Piece | Where | Note |
|---|---|---|
| **Session chokepoint** | `credentials/service/Sg__Aws__Session.py` — `from_context()`, `boto3_client_from_context(svc, region)`, `session_for(role)` | `session_for` already does STS `AssumeRole` + caches temp creds when a role config has `assume_role_arn`. **This is the join point.** |
| **Keyring store** | `osx/keyring/*`, `credentials/service/Credentials__Store.py` | macOS Keychain via `/usr/bin/security`. Roles: `sg.config.role.<name>` (region, `assume_role_arn`, account_id) + `sg.aws.<role>` (keys). |
| **Current-role context** | `credentials/service/Sg__Aws__Context.py` + env `SG_CREDENTIALS__CURRENT_ROLE` | Per-shell (`eval $(sg credentials switch dev)`) or in-process (REPL `as <role>`). |
| **Credential commands** | `sg credentials *` (list/add/switch/show/test/whoami) and `sg aws creds *` (scoped STS get, scope CRUD, audit) | Rich surface already; we reuse, not replace. |
| **Transparent assume — the model** | `sg_compute_specs/vault_publish/setup/service/Setup__IAM.py::_detect_iam_role()` (~L269–298) + `aws/iam/service/IAM__AWS__Client.py::client()` | If already `iam-admin` → use silently; else if `iam-admin` exists → assume it with a one-line notice; route the client through `session.boto3_client(role, 'iam')`. **Generalise this.** |

### The gap that caused the traceback

Two boto3-construction patterns coexist:

- **Pattern A — through the chokepoint** (7 classes: S3, ECR, Fargate, CloudTrail, ALB,
  Bedrock×2): `session.boto3_client_from_context(...)`. Role/assume/region all flow here.
- **Pattern B — bypass** (CloudFront, Logs, Firehose, `Elastic__AWS__Client`) **plus the
  LETS S3 boundaries** (`S3__Inventory__Lister`, `S3__Object__Fetcher`) and EC2 (osbot
  `EC2()`): call `boto3.client(...)` directly. **No role, no assume, no central error
  handling.** `tui sync` uses the LETS boundaries → raw `NoCredentialsError`.

So "generic across all `sg aws`" has a prerequisite: **converge the bypassers onto the
chokepoint** (or wrap them), so there is one place to resolve auth and catch failures.

---

## 3. What we will build

Four generic components + one case-study instantiation + a rollout.

### 3.0 The reuse contract — built once vs per section

This is the spine of the design. Everything heavy is built **once** in a shared layer
(`aws/_shared/auth/`); each `sg aws *` section then onboards with a tiny, declarative
footprint. If onboarding section #2 needs new auth *logic*, the abstraction has failed.

| Built ONCE (generic, section-agnostic) | Added PER section (small, declarative) |
|---|---|
| `Sg__Aws__Session` chokepoint (already exists) | one `Schema__AWS__Role__Profile` registry entry (role name + least-priv statements) |
| `AWS__Auth__Resolver` (transparent assume) | `@aws_auth_guard(family='…')` on the section's commands (one line each, or one on the sub-app) |
| `AWS__Auth__Error` + interactive resolution menu | — |
| shared client base / converged `client()` seam | clients just inherit it (no per-service auth code) |
| generic `… iam {show,plan,create,update,test,delete}` verb engine | mount the verb engine under the section, pointed at its profile |

Concretely, onboarding `sg aws ec2` after `lets cf` should be: **add one profile entry,
mount the iam verbs, decorate the commands.** No new classes, no new error handling.

### 3a. Role-profile registry (generic, declarative)
A single source of truth mapping **command family → least-privilege intent**:
```
Schema__AWS__Role__Profile:
  family        : 'el-lets-cf'                 # stable id
  role_name     : 'sg-lets-cf'                 # the IAM role we assume / create
  statements    : [ {actions, resources, effect} ... ]   # the least-priv policy
  description   : '...'
```
`AWS__Role__Profiles` registry holds one per family. Both the IAM CRUD (to *create* the
role) and the auth resolver (to *assume* it) read this — one definition, no drift between
"what we grant" and "what we assume".

### 3b. Generic transparent assume-role resolver
Generalise `_detect_iam_role` into `AWS__Auth__Resolver.resolve(family)`:
- if the current context role already **is** the family role (or a superset like admin) → use silently;
- else if the family role is reachable (exists in account / keyring) → **assume it**, printing one dim line: `for sg el lets cf, assuming role 'sg-lets-cf'`;
- else → no transparent path; defer to the error guard (3c).
Assume is done via `Sg__Aws__Session` (extend it with "assume role by name/ARN from the
current context", deriving the ARN from the cached account id). Temp creds cached per run.

### 3c. Generic auth-error guard + interactive resolution
A typed error + a CLI-boundary handler:
- `Sg__Aws__Auth__Error` wraps `NoCredentialsError` / `ClientError(AccessDenied|
  ExpiredToken|UnauthorizedOperation|InvalidClientTokenId)` with context (service,
  operation, family).
- A decorator/contextmanager (`with aws_auth_guard(family='el-lets-cf'):`) wraps command
  bodies. On a caught auth error it prints a clear cause and offers choices (Typer prompt;
  in a TUI, a modal):
  1. **Assume the family role** `sg-lets-cf` (recommended; runs 3b explicitly).
  2. **Switch to a stored credential** — list roles from the keyring, pick one.
  3. **Show the fix** — the exact `sg credentials switch …` / `sg el lets cf iam create` commands.
  4. Abort.
- Non-interactive (piped/CI): print the cause + remediation commands and exit non-zero —
  never a traceback.

### 3d. Client convergence (prerequisite, incremental)
Route the bypassers through the chokepoint so 3a–3c actually cover them:
- Give `CloudFront/Logs/Firehose__AWS__Client` and the LETS `S3__Inventory__Lister` /
  `S3__Object__Fetcher` a `session`-based `client()` (Pattern A), keeping their existing
  `client()`/`s3_client()` seam name so tests still subclass-override (no mocks).
- This is the single most important enabler and can land first, behind the existing seams,
  with zero behaviour change when creds are present.

### 3e. `sg el lets cf iam` CRUD — the case study
Follows `library/guides/v0.2.31__setup_cli_pattern.md` (areas, verbs, drift-first,
mutation gates, self-verify). Commands:
| Command | Does |
|---|---|
| `sg el lets cf iam show` | the live `sg-lets-cf` role + attached policy, **drift vs the registry** (3a) |
| `sg el lets cf iam plan` | what `create`/`update` would change (dry-run; read-only) |
| `sg el lets cf iam create` | ensure the role: trust policy (operator principal may assume) + least-priv policy from 3a. **Uses the existing transparent `iam-admin` path** to do the create. |
| `sg el lets cf iam update` | reconcile live policy → registry (drift-first) |
| `sg el lets cf iam test` | assume `sg-lets-cf` and dry-run the key calls (ListBucket, GetObject, cloudfront/logs/firehose reads) — prove the privs are sufficient and not excessive |
| `sg el lets cf iam delete` | remove role + policy (mutation-gated) |
Mutations gated by an env flag (matches the s3/logs `*_ALLOW_MUTATIONS` convention).

### 3f. Rollout to all `sg aws *`
Once proven: add a `Schema__AWS__Role__Profile` per family and a uniform `… iam` verb set
(or a top-level `sg aws iam role <family> {show|plan|create|update|test|delete}`). The
resolver (3b) and guard (3c) are family-agnostic — only the registry grows.

---

## 4. How — phasing

| Phase | Deliverable | Risk |
|---|---|---|
| **P1** | 3d client convergence (CF/Logs/Firehose + LETS S3 boundaries → chokepoint), behind existing seams. Tests stay green (subclass-override seams unchanged). | low — internal, no UX change |
| **P2** | 3c generic auth guard + interactive resolution; wrap `sg el lets cf *` command bodies first. Replaces the raw traceback with the menu. | low/med — needs careful non-TTY behaviour |
| **P3** | 3a role-profile registry + the concrete `el-lets-cf` profile (policy from §5). | low |
| **P4** | 3e `sg el lets cf iam` CRUD (create/show/plan/update/test/delete) via the iam-admin path. | med — touches real IAM; mutation-gated; dry-run first |
| **P5** | 3b transparent assume wired into `sg el lets cf *` (assume `sg-lets-cf` automatically). | med — assume-by-name helper on Sg__Aws__Session |
| **P6** | Generalise registry + verbs to other `sg aws *` families (rollout). | incremental |

Each phase commits independently with tests (no mocks; subclass the boto3 seams / inject a
fake STS). P1 alone already fixes the reported `tui sync` traceback (it would then surface
through the guard once P2 lands).

---

## 5. Least-privilege policy for `sg el lets cf *` (the registry entry)

Derived from tracing every `cf_app` command. ES/Kibana access is **HTTP to the ephemeral
stack, not an AWS API** → no IAM action needed (verify during P3).

| Action | Resource | Used by |
|---|---|---|
| `s3:ListBucket` | `arn:aws:s3:::745506449035--sgraph-send-cf-logs--eu-west-2` | inventory, events, sg-send, consolidate, tui, sync, cache |
| `s3:GetObject` | `…cf-logs--eu-west-2/cloudfront-realtime/*` | events, sg-send, consolidate, tui, sync |
| `s3:PutObject` | `…cf-logs--eu-west-2/lets/*` | **consolidate only** (split into a separate statement so read-only operators don't get write) |
| `cloudfront:ListDistributions` | `*` (global) | tui architecture |
| `logs:DescribeLogGroups` | `*` (or scoped to a prefix) | tui architecture |
| `firehose:ListDeliveryStreams` | `*` | tui architecture |
| `firehose:DescribeDeliveryStream` | `arn:aws:firehose:eu-west-2:745506449035:deliverystream/*` | tui architecture |

Trust policy: allow the operator's base identity / account root to `sts:AssumeRole`.

---

## 6. Decisions / open questions (need a steer)

1. **Role name & granularity.** One role `sg-lets-cf` for the whole family (simpler, the
   recommended start), or split read vs write (consolidate's `PutObject`)? *Recommend: one
   role now, split later.*
2. **Inline vs managed policy.** Inline on the role (self-contained, easy drift-check) vs a
   standalone managed policy (reusable). *Recommend: inline for the case study.*
3. **How the family role is referenced.** Compute the ARN from the cached account id +
   `role_name` (no extra keyring entry), or store a keyring role entry like `iam-admin`?
   *Recommend: computed ARN, with optional keyring override.*
4. **Auto-assume default on/off.** Should `sg el lets cf *` assume `sg-lets-cf`
   automatically (transparent, like iam-admin), or only after the user opts in once?
   *Recommend: transparent by default once the role exists, with the one-line notice.*
5. **Scope of P1 convergence.** Migrate all bypassers at once, or just the LETS S3
   boundaries that caused the bug first? *Recommend: LETS boundaries + CF/Logs/Firehose
   (the `sg el lets cf` surface) first; other sections during P6.*

---

## 7. Out of scope (for now)
- Replacing the keyring/credentials commands (we build on them).
- Cross-account / SSO flows beyond the existing assume-role.
- Fine-grained per-command roles (we start at per-family; tighten later).
- Non-AWS auth (vault, Elastic HTTP) — separate concern.
