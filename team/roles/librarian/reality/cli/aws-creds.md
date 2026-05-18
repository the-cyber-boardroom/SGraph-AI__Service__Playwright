---
title: "Reality — cli/aws-creds"
file: aws-creds.md
author: Dev (Claude)
date: 2026-05-17
status: LIVE — implemented in v0.2.29 Slice G; updated v0.2.30 Open-2 (typed primitives)
parent: cli/index.md
---

# cli/aws-creds — `sg aws creds` Surface

**Last updated:** 2026-05-17
**Slice:** v0.2.29 Slice G
**Branch:** `claude/aws-primitives-support-uNnZY`

> **AppSec sign-off required before merge to main.** The STS assume_role surface
> creates short-lived credentials from a local scope catalogue — no keys in Git,
> audit log at 0600 — but the security team should validate the TTL-cap
> enforcement and audit log completeness before this is treated as prod-ready.

---

## EXISTS (code-verified, 2026-05-17)

### Location

`sgraph_ai_service_playwright__cli/aws/creds/`

Registered in `Cli__Aws` as `app.add_typer(creds_app, name='creds')` (pending registration — see below).

### CLI verbs

| Verb | Mutating | Gate required |
|------|----------|---------------|
| `get --scope <name> [--role-hint <arn>] [--ttl 1h] [--shell-export] [--json]` | no | — |
| `list-scopes [--json]` | no | — |
| `scope show <name> [--json]` | no | — |
| `scope add --name <name> --role <arn> [--max-ttl 1h] [--yes] [--json]` | yes | `SG_AWS__CREDS__ALLOW_MUTATIONS=1` |
| `scope remove <name> [--yes]` | yes | `SG_AWS__CREDS__ALLOW_MUTATIONS=1` |
| `scope update <name> [--role] [--max-ttl] [--yes] [--json]` | yes | `SG_AWS__CREDS__ALLOW_MUTATIONS=1` |
| `audit list [--caller] [--scope] [--since 1h] [--json]` | no | — |
| `audit show <assumption_id> [--json]` | no | — |

### Production files

| File | Role |
|------|------|
| `cli/Cli__Creds.py` | All Typer commands + sub-apps (`scope`, `audit`) |
| `service/Creds__Scope__Catalogue.py` | Local JSON catalogue at `~/.sg/aws/creds/scopes.json` (0600) |
| `service/Creds__STS__Client.py` | boto3 STS `assume_role` boundary with `client()` seam |
| `service/Creds__Audit__Log.py` | Append-only JSONL log at `~/.sg/aws/creds/audit.jsonl` (0600) |
| `service/Creds__TTL__Parser.py` | Parses `'1h'`, `'30m'`, `'120s'` to seconds |
| `schemas/Schema__Creds__Scope.py` | name, role_arn, max_ttl, created_at |
| `schemas/Schema__Creds__Assumption.py` | assumption_id, scope_name, role_arn, caller, assumed_at, expires_at, access_key_id, session_token |
| `schemas/Schema__Creds__Export.py` | access_key_id, secret_access_key, session_token, expiration, region |
| `primitives/Safe_Str__Creds__Assumption_Id.py` | REPLACE, allow_empty — assumption UUID |
| `primitives/Safe_Str__Creds__Scope_Name.py` | REPLACE, allow_empty — scope catalogue key |
| `primitives/Safe_Str__Creds__Caller.py` | REPLACE, allow_empty — ARN from GetCallerIdentity |
| `primitives/Safe_Str__Creds__Timestamp.py` | REPLACE, allow_empty — ISO-8601 string |
| `primitives/Safe_Str__Creds__Access_Key_Id.py` | REPLACE, allow_empty — AWS AKIA… key |
| `primitives/Safe_Str__Creds__Session_Token.py` | REPLACE, allow_empty — STS session token |
| `primitives/Safe_Str__Creds__Secret_Access_Key.py` | REPLACE, allow_empty — AWS secret key |
| `primitives/Safe_Str__Creds__Max_TTL.py` | REPLACE, allow_empty — e.g. `1h`, `30m` |
| `collections/List__Schema__Creds__Scope.py` | Typed list of scopes |
| `collections/List__Schema__Creds__Assumption.py` | Typed list of assumption records |

### Security properties

- Catalogue file and audit log are created with permissions 0600 (owner read/write only).
- Every assumption is logged before credentials are returned to the caller.
- The requested TTL is capped to the scope's `max_ttl`; exceeding it exits with code 1.
- No credentials are stored in the audit log — only `access_key_id` and `session_token` (no `secret_access_key`).
- Mutation gate (`SG_AWS__CREDS__ALLOW_MUTATIONS=1`) is required for all catalogue mutations.

### Tests

Location: `tests/unit/sgraph_ai_service_playwright__cli/aws/creds/`

| Test file | Coverage |
|-----------|----------|
| `cli/test_Cli__Creds.py` | 10 cases: list-scopes empty/populated, scope show/missing, scope add (gate + success), scope remove gate, get unknown/success/TTL-cap |
| `service/test_Creds__Scope__Catalogue.py` | 8 cases: load empty, add, get, get-missing, list-sorted, remove, remove-missing, overwrite |
| `service/test_Creds__STS__Client.py` | 6 cases: assume_role keys, key prefix, expiry timing, uniqueness, caller-identity, short duration |

Total: 24 unit tests, all green.

### In-memory test helpers

`tests/unit/sgraph_ai_service_playwright__cli/aws/creds/service/Creds__Scope__Catalogue__In_Memory.py`
`tests/unit/sgraph_ai_service_playwright__cli/aws/creds/service/Creds__STS__Client__In_Memory.py`

Both are real subclasses — no mocks, no patches.

### v0.2.30 Open-2 — schema fields typed

Previously all `str` fields in creds schemas were raw Python strings. Open-2 replaced them:
- `Schema__Creds__Assumption`: `assumption_id`, `scope_name`, `caller`, `assumed_at`, `expires_at`, `access_key_id`, `session_token` → typed; `role_arn → Safe_Str__AWS__Role__ARN`
- `Schema__Creds__Export`: `access_key_id`, `secret_access_key`, `session_token`, `expiration` → typed; `region → Safe_Str__AWS__Region`
- `Schema__Creds__Scope`: `name`, `max_ttl`, `created_at` → typed; `role_arn → Safe_Str__AWS__Role__ARN`

---

## NOT implemented in this slice

- IAM / SCP policy validation before assuming the role
- Multi-account scope federation
- Integration tests requiring live AWS credentials
- Vault-backed scope storage (scopes live in `~/.sg/aws/creds/scopes.json` only)
- `Cli__Aws` registration (`creds_app` not yet wired into parent `Cli__Aws.py`)

---

## See also

- User guide: [`library/docs/cli/sg-aws/15__creds.md`](../../../../../library/docs/cli/sg-aws/15__creds.md)
- Parent: [`cli/index.md`](index.md)
