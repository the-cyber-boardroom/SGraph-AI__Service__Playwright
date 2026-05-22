---
title: "Reality — cli/aws-auth"
file: aws-auth.md
author: Dev (Claude)
date: 2026-05-21
status: LIVE — implemented v0.2.40 on branch claude/review-cf-logging-docs-QYfEq (unit-tested with in-memory fakes; live IAM/STS unverified — see caveats)
parent: cli/index.md
---

# cli/aws-auth — Shared AWS auth layer (`aws/_shared/auth/`)

**Last updated:** 2026-05-21
**Slice:** v0.2.40
**Branch:** `claude/review-cf-logging-docs-QYfEq`

The generic credential-resolution + role-provisioning layer that sits under every
`sg aws` / `sg el lets cf` command. It turns a raw `NoCredentialsError` into a helpful
menu, and lets a command family transparently assume a scoped least-privilege role.

> Distinct from [`aws-creds.md`](aws-creds.md): that documents the `sg aws creds`
> STS *scope catalogue* (`~/.sg/aws/creds/scopes.json`). This layer is the
> keyring-backed `Sg__Aws__Session` chokepoint plus the new `aws/_shared/auth/`
> engine. They do not share code.

---

## EXISTS (code-verified, 2026-05-21)

### Location

`sgraph_ai_service_playwright__cli/aws/_shared/auth/`

### The chokepoint (P1 — convergence)

`Aws__Session__Factory.boto3_client_via_context(service, region='')` is **the one place
a boto3 client is born** for the converged surface. It routes through
`Sg__Aws__Session` (keyring role → STS AssumeRole → cached temp creds) with a
bare-boto3 fall-through when no SG role is set (safe on CI / Fargate / Lambda IMDS).

Clients that previously called `boto3.client()` directly now call this from their
existing seam (seam names unchanged, so tests still subclass-override):

| Client | Seam |
|--------|------|
| `aws/cf/service/CloudFront__AWS__Client` | `client()` |
| `aws/logs/service/Logs__AWS__Client` | `client()` |
| `aws/firehose/service/Firehose__AWS__Client` | `client()` |
| `elastic/lets/cf/inventory/service/S3__Inventory__Lister` | `s3_client(region)` |
| `elastic/lets/cf/events/service/S3__Object__Fetcher` | `s3_client(region)` |

(`aws/s3/service/S3__AWS__Client` already used the chokepoint.)

### The auth-error guard (P2)

| File | Role |
|------|------|
| `AWS__Auth__Classifier.py` | `is_auth_error(exc)` / `auth_error_cause(exc)` — detects `NoCredentialsError` + botocore `ClientError` auth codes (AccessDenied, ExpiredToken, …). Pure. |
| `AWS__Auth__Guard.py` | `@aws_auth_guard(family='')` decorator + `run_guarded(fn, family, store, chooser)`. On an auth error: interactive (TTY) → list stored keyring credentials, pick one, set it on `Sg__Aws__Context`, **retry the command in-process**; non-interactive → print remediation, exit 2. `store` + `chooser` injectable → tested with no AWS, no TTY. |

### Role-profile registry (P3)

| File | Role |
|------|------|
| `AWS__Role__Profiles.py` | `register / get_profile / all_families`; renders a profile to `policy_document` (inline IAM JSON), `trust_policy_document(account_id)` (account-root trust), `role_arn`. The single source of truth read by both the provisioner and the assumer — granted vs assumed privilege never drift. |
| `schemas/Schema__AWS__Role__Profile.py` | `family`, `role_name`, `description`, `statements` |
| `schemas/Schema__AWS__Policy__Statement.py` + `List__AWS__Policy__Statement.py` | `sid`, `effect`, `actions`, `resources` |

Per-family footprint: a family declares its profile in its own module and self-registers.
First onboarded family: `elastic/lets/cf/iam/cf_role_profile.py` → **`el-lets-cf` / role
`sg-lets-cf`** (S3 list+get on the CF-logs bucket, PutObject only for consolidate,
cloudfront/logs/firehose read for the Architecture screen). Onboarding another section =
one profile file + one import line in `AWS__Role__Profiles._ensure_loaded()`.

### Role provisioner (P4)

| File | Role |
|------|------|
| `AWS__Role__Provisioner.py` | `plan` (diff live role vs profile → `Schema__AWS__Role__Plan`), `apply` (create-or-update, idempotent), `delete`, `resolve_account_id` (STS). Generic — drives create/diff/delete for any family through `IAM__AWS__Client`. |
| `schemas/Schema__AWS__Role__Plan.py` | exists / in_sync / actions_to_add / actions_to_remove / policy_json / trust_json |

`IAM__AWS__Client` gained `create_role_with_trust(role, trust_json, description)` (raw
account-root trust, which the service-principal `create_role` cannot express) and
`update_assume_role_policy_raw(role, trust_json)`.

### Transparent assume (P5)

| File | Role |
|------|------|
| `AWS__Auth__Context.py` | process-level **active family** (`set/get/clear_active_family`). The base identity is `Sg__Aws__Context.current_role` (assume *from*); this is the family we assume *into*. |
| `AWS__Auth__Resolver.py` | when a family is active, the factory asks the resolver for a client → it assumes the family's role from the base identity, prints a one-line notice once per process (stderr), and caches the assumed session. Returns `None` (→ fall back to base identity, then the guard menu) if the role is absent or assume is denied. `clear_cache()` test hook. |

`Sg__Aws__Session` gained `base_session_from_context()`, `account_id_via_sts()`,
`assume_arn(role_arn)` (the STS boundary stays in this class).

`aws_auth_guard(family)` sets/clears the active family for the wrapped command, so
least-privilege assume is the **default path**, not an opt-in. `aws_auth_guard('')`
(empty family) catches auth errors **without** assuming — used by the `iam` management
commands, which must run as the base admin identity.

### Where the guard is wired

- Native: `sg el lets cf sync`, `sg el lets cf cache` (`local/cli/Cli__CF__Local.py`).
- TUI (S3-touching): `sg el lets cf tui {traffic,files,inspect,architecture,sync}`
  (`tui/cli/Cli__CF__Tui.py`). `cache` / `diagnose` touch no AWS → ungated.
- IAM management: `sg el lets cf iam {show,plan,create,delete}` (guard with empty family).

### Tests

`aws/_shared/auth/tests/` — classifier + guard, role-profile registry, provisioner,
resolver + context + factory fallback. `elastic/lets/cf/iam/tests/` — the iam CLI with an
injected in-memory `Fake__IAM`. All real subclasses, **no mocks, no patches**. Full
regression green across `aws/`, `elastic/lets/cf/`, `credentials/`, `tui/` (155).

---

## NOT implemented / caveats

- **Live IAM/STS unverified.** `create`/`update`/`delete`/`test` and the real assume are
  unit-tested against an in-memory IAM fake only; validate with `sg el lets cf iam
  create` + `iam test` on a credentialed console.
- The interactive guard menu's "retry in-process" path re-invokes the whole command
  (fine for idempotent reads; create/delete re-prompt the gate + confirm).
- Only one family (`el-lets-cf`) is registered today.

---

## See also

- Plan: [`team/comms/plans/v0.2.40__sg-aws-auth-and-lets-cf-iam`](../../../comms/plans/)
- LETS cf command family: [`lets/index.md`](../lets/index.md)
- Keyring credentials chokepoint: `credentials/service/Sg__Aws__Session.py`
- Parent: [`cli/index.md`](index.md)
