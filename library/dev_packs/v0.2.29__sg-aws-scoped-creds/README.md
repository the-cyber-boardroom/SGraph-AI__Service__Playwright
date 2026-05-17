---
title: "v0.2.29 — sg aws creds — scoped credential delivery (Slice G)"
file: README.md
author: Architect (Claude)
date: 2026-05-17
status: PROPOSED — independent sibling pack of v0.2.29__sg-aws-primitives-expansion
size: M — ~1300 prod lines, ~600 test lines, ~2.5 calendar days
parent_umbrella: library/dev_packs/v0.2.29__sg-aws-primitives-expansion/
source_brief: team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__arch-brief__dynamic-credential-delivery-service.md
feature_branch: claude/aws-primitives-support-uNnZY-creds
---

# `sg aws creds` — Slice G

Local scoped-credential delivery via STS AssumeRole. Each command requests the privileges it needs, gets temporary credentials, performs the action, and the credentials expire. **Phase 1 + Phase 2 only** — local service with vault-stored scope catalogue. Phase 5 (deployed service) and Phase 6 (audit dashboard) defer to v0.2.30.

> **PROPOSED — does not exist yet.** Cross-check `team/roles/librarian/reality/security/` and `cli/aws-creds.md` before describing anything here as built.

---

## Where this fits

This is **one of eight sibling slices** of the v0.2.29 milestone. The umbrella pack at [`v0.2.29__sg-aws-primitives-expansion/`](../v0.2.29__sg-aws-primitives-expansion/README.md) owns the locked decisions, the [Foundation brief](../v0.2.29__sg-aws-primitives-expansion/02__common-foundation.md), and the [orchestration plan](../v0.2.29__sg-aws-primitives-expansion/03__sonnet-orchestration-plan.md). **Read the umbrella first.**

Independent of all other v0.2.29 slices. **Requires AppSec sign-off before merge** — STS AssumeRole and a local scope catalogue are security-sensitive.

Naming: this new namespace is `sg aws creds` (short, action-oriented). It is **separate** from the existing `sg aws credentials` namespace (which manages long-lived per-role AWS access keys — the credentials-store layer landed in v0.2.28). Both can coexist; the user-guide page makes the distinction clear.

---

## Source brief

[`v0.27.43__arch-brief__dynamic-credential-delivery-service.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__arch-brief__dynamic-credential-delivery-service.md) is ground truth.

This slice ships:

- **Phase 1** — Local credential service with 5-10 scoped roles
- **Phase 2** — Scope catalogue stored in a vault, version-controlled

Deferred to v0.2.30:

- Phase 3 — SG command migration to scoped credentials
- Phase 4 — Agent CLI migration
- Phase 5 — Deployed credential service
- Phase 6 — Audit dashboard

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/creds/` (Foundation ships the skeleton; you fill in the bodies)

### Verbs

| Verb | Tier | Notes |
|------|------|-------|
| `get --scope <name> [--role-hint <name>] [--ttl <duration>]` | read-only (STS-side) | Returns temporary credentials for the scope; default TTL 1h, cap 12h |
| `list-scopes` | read-only | All scopes in the catalogue |
| `scope show <name>` | read-only | The scope: name, mapped role ARN, policy summary, authorised callers |
| `scope add --name X --role <arn> [--allowed-callers <user-list>] [--max-ttl <duration>]` | mutating | Adds a scope to the catalogue (vault commit) |
| `scope remove <name>` | mutating | Removes a scope (vault commit) |
| `scope update <name> --field value [--field value ...]` | mutating | Edits scope metadata (vault commit) |
| `audit list [--caller X] [--scope X] [--since <duration>]` | read-only | Tail of the assumption log |
| `audit show <assumption-id>` | read-only | Full record: caller, scope, role, timestamp, expiry, success/failure |

**Mutation gate:** `SG_AWS__CREDS__ALLOW_MUTATIONS=1` required for `scope add/remove/update`. `get` does not require it — it's the whole point of the system that getting credentials is friction-free.

### Scope catalogue layout (vault)

```
<vault-root>/aws/creds-catalogue/
├── catalogue.json                       # top-level index
├── scopes/<scope-name>.json             # one file per scope (Schema__Scope__Definition)
└── audit/<YYYY-MM>/assumptions.jsonl    # monthly assumption logs
```

**Vault writer integration:** the layout above is realised via `sg_compute/vault/Vault__Spec__Writer` (the BV2.9 canonical writer) — `Creds__Catalogue__Vault__Writer` wraps it and registers `aws-creds-catalogue` as a vault namespace, then maps the on-disk layout to the writer's `(namespace, stack_id, handle, bytes)` interface. Same translation pattern as Bedrock's `Bedrock__Vault__Writer`.

### API stability commitment (Phase 1 → Phase 5)

The Phase 5 swap from "local service" to "deployed service" must be a server swap, not a client rewrite. To enforce that:

- `sg aws creds get --scope <name>` returns `Schema__Scoped__Credentials` with fields `{access_key, secret_key, session_token, expiration, scope, role_arn, request_id}`. **This shape is frozen by this slice** — Phase 5 cannot add required fields or change types.
- The local `Aws__Caller__Identity__Local.resolve()` returns the same `Schema__Caller__Identity` shape that Phase 5's signed-request resolver will return. Optional fields (`signed_request_id`, `request_ip`) stay empty in Phase 1.
- A `Test__Phase_5__Stability` test fixture composes a fake remote service over the same interface to prove the client code path is reusable.

Each `scopes/<scope-name>.json` carries:

```
{
  "name": "lambda:list",
  "role_arn": "arn:aws:iam::123456789012:role/sg-scope-lambda-list",
  "max_ttl_seconds": 3600,
  "allowed_callers": ["dinis@laptop", "ci@github-actions"],
  "policy_summary": "lambda:ListFunctions on *",
  "created_at": "2026-05-17T...",
  "created_by": "...",
  "schema_version": "1"
}
```

### Authorisation enforcement

For Phase 1 (local), the caller's identity is the OS user running the command (`Aws__Caller__Identity__Local.resolve()` returns `<user>@<hostname>`). The scope definition's `allowed_callers` list gates `get`.

For Phase 5 (deferred — deployed service), the caller identity comes from signed requests — out of scope here. The local code path is designed so the swap is non-invasive.

### Assumption logging

Every `get` call (success or failure) writes one line to the monthly audit JSONL with:

```
caller | scope | role_arn | requested_ttl | granted_ttl | timestamp | success | error_code (if any) | session_token_fingerprint (for correlation)
```

The session token is never logged in full — only a SHA-256 fingerprint for correlation.

---

## Production files (indicative)

```
aws/creds/
├── cli/
│   ├── Cli__Creds.py
│   └── verbs/
│       ├── Verb__Creds__Get.py
│       ├── Verb__Creds__List_Scopes.py
│       ├── Verb__Creds__Scope__Show.py
│       ├── Verb__Creds__Scope__Add.py
│       ├── Verb__Creds__Scope__Remove.py
│       ├── Verb__Creds__Scope__Update.py
│       ├── Verb__Creds__Audit__List.py
│       └── Verb__Creds__Audit__Show.py
├── service/
│   ├── Creds__Local__Service.py            # Phase 1 orchestrator
│   ├── Creds__STS__Client.py               # wraps Sg__Aws__Session (STS AssumeRole)
│   ├── Creds__Cache.py                     # in-memory cache keyed by (caller, scope) tuple
│   ├── Creds__Catalogue__Vault__Reader.py
│   ├── Creds__Catalogue__Vault__Writer.py
│   ├── Creds__Audit__Log__Writer.py
│   ├── Creds__Caller__Identity__Local.py
│   └── Creds__Authorisation__Gate.py
├── schemas/                                # Schema__Scope__Definition, Schema__Creds__Bundle, Schema__Assumption__Record, etc.
├── enums/                                  # Enum__Creds__TTL__Bracket, Enum__Caller__Identity__Source
├── primitives/                             # Safe_Str__Scope__Name, Safe_Str__Role__ARN, Safe_Str__Session__Token__Fingerprint
└── collections/                            # List__Schema__Scope__Definition, List__Schema__Assumption__Record
```

---

## What you do NOT touch

- Any other surface folder under `aws/`
- `aws/_shared/` (Foundation-owned)
- The existing `sgraph_ai_service_playwright__cli/credentials/` package (the long-lived-credentials store) — orthogonal concern, untouched
- `Sg__Aws__Session` (the v0.2.28 client seam) — you USE it to call STS; you do not modify it
- Phase 3 onwards (SG command migration) — separate v0.2.30 pack
- The deployed credential service (Phase 5) — separate v0.2.30 pack

---

## Acceptance

```bash
# bootstrap a vault catalogue with seed scopes
SG_AWS__CREDS__ALLOW_MUTATIONS=1 sg aws creds scope add \
    --name iam:read-only \
    --role arn:aws:iam::123456789012:role/sg-scope-iam-read-only \
    --max-ttl 1h --yes

sg aws creds list-scopes                                                # → iam:read-only visible
sg aws creds scope show iam:read-only

# get credentials
sg aws creds get --scope iam:read-only                                  # → AWS_ACCESS_KEY_ID / SECRET / SESSION_TOKEN / EXPIRATION
eval "$(sg aws creds get --scope iam:read-only --shell-export)"        # exports into shell
aws sts get-caller-identity                                             # → confirms the assumed role

# audit
sg aws creds audit list --since 1h
sg aws creds audit show <assumption-id>

# unauthorised caller
SG_AWS__CREDS__ALLOW_MUTATIONS=1 sg aws creds scope update iam:read-only \
    --allowed-callers "other-user@other-host" --yes
sg aws creds get --scope iam:read-only                                  # → Authorisation__Refused — caller not in allowed list

# scope removal
SG_AWS__CREDS__ALLOW_MUTATIONS=1 sg aws creds scope remove iam:read-only --yes
sg aws creds list-scopes                                                # → empty

# tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/creds/ -v
SG_AWS__CREDS__INTEGRATION=1 pytest tests/integration/sgraph_ai_service_playwright__cli/aws/creds/ -v
```

---

## Deliverables

1. All files under `aws/creds/` per the layout above
2. Unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/creds/`
3. Integration tests under `tests/integration/sgraph_ai_service_playwright__cli/aws/creds/` (gated; provisions a real `sg-scope-test-*` role and AssumeRoles into it)
4. Initial scope catalogue seed (5 scopes minimum): `iam:read-only`, `lambda:list`, `s3:read:specific:sg-test-bucket`, `route53:read-only`, `cloudtrail:read-only`. Committed to the dev vault as part of the PR.
5. New user-guide page `library/docs/cli/sg-aws/15__creds.md` — must clearly distinguish `sg aws creds` (this slice, scoped STS) from `sg aws credentials` (existing, long-lived keys)
6. One row added to `library/docs/cli/sg-aws/README.md` "at-a-glance command map"
7. Reality-doc update: new `team/roles/librarian/reality/cli/aws-creds.md` + cross-reference from `security/` index and from `cli/aws-iam.md`

---

## Risks to watch

- **Role-trust-policy provisioning.** The roles `get` assumes must be pre-provisioned with a TrustPolicy allowing the SG account / caller principal. The pack does not auto-create roles in this slice (that's `iam role create` — already exists in the existing IAM CLI). Document the trust-policy template in the user-guide.
- **Credential caching.** Cache by (caller, scope) tuple in-memory; never persist to disk. On expiry, transparently re-assume. Cache TTL = min(`granted_ttl`, `max_ttl`) - 60s safety margin.
- **Naming collision with `sg aws credentials`.** Confusing for users. Mitigation: distinct verb sets (`creds get / scope` vs `credentials add / switch`), and the user-guide page leads with a comparison table.
- **Local catalogue path.** The vault location is `$SG_VAULT_ROOT/aws/creds-catalogue/`. If `$SG_VAULT_ROOT` isn't set, refuse to operate (clear error, link to the vault-setup doc). Never silently fall back to `~/.sg/`.
- **Audit log integrity.** The log file is append-only and group-restricted (`0660`); rotation is monthly. Do not allow `audit list/show` to mutate the file inadvertently.
- **Cache poisoning across users.** The in-memory cache is per-process; nothing crosses users. Document this as an invariant — never share the process between users.

---

## Commit + PR

Branch: `claude/aws-primitives-support-uNnZY-creds`

Commit message: `feat(v0.2.29): sg aws creds — local scoped STS credential delivery (Phases 1+2)`.

PR target: `claude/aws-primitives-support-uNnZY`. Tag the Opus coordinator **AND request AppSec review** before merge. Do **not** merge yourself.

---

## Cancellation / descope

Independent. Cancelling defers the scoped-credentials workstream entirely; v0.2.30 IAM-graph Phase 5/6 (SG command lockdown) cannot proceed without it. No other v0.2.29 slice is affected.
