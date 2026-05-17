---
title: "sg aws creds — User Guide"
file: 15__creds.md
author: Dev (Claude)
date: 2026-05-17
status: LIVE — implemented in v0.2.29 Slice G
appsec-note: AppSec sign-off required before promoting to production use.
---

# `sg aws creds` — Scoped STS Credential Delivery

Short-lived IAM credentials on demand. Define named scopes (scope → IAM role ARN),
then call `sg aws creds get --scope <name>` to get temporary credentials via
`sts:AssumeRole`. Every assumption is audit-logged locally.

> **Note:** `sg aws creds` delivers *scoped temporary credentials* via STS.
> It is distinct from `sg aws credentials` (long-lived keychain-backed credentials store).

## Mutation gate

```bash
export SG_AWS__CREDS__ALLOW_MUTATIONS=1   # required for scope add/remove/update
```

Read-only verbs (`get`, `list-scopes`, `scope show`, `audit list`, `audit show`) never require a gate.

---

## Verbs

### `get` — Assume a role for a named scope

```bash
sg aws creds get --scope dev                         # assume role for 'dev', 1h TTL (default)
sg aws creds get --scope dev --ttl 30m               # shorter TTL (must not exceed scope max-ttl)
sg aws creds get --scope prod --role-hint arn:...    # override the role ARN for this call only
sg aws creds get --scope dev --json                  # JSON with all four credential fields
sg aws creds get --scope dev --shell-export          # export AWS_* env vars to stdout (eval-safe)
```

**JSON output shape:**

```json
{
  "access_key_id":     "ASIAxxxxxxxxxxxxxxxx",
  "secret_access_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "session_token":     "FwoGZX...",
  "expiration":        "2026-05-17T20:43:00+00:00",
  "region":            "eu-west-1"
}
```

**Shell-export usage:**

```bash
eval "$(sg aws creds get --scope dev --shell-export)"
aws s3 ls s3://my-bucket
```

Every `get` call appends an entry to `~/.sg/aws/creds/audit.jsonl`.
The audit entry contains `access_key_id` and `session_token` but **never** `secret_access_key`.

---

### `list-scopes` — List all defined scopes

```bash
sg aws creds list-scopes
sg aws creds list-scopes --json
```

---

### `scope show` — Show one scope definition

```bash
sg aws creds scope show dev
sg aws creds scope show dev --json
```

---

### `scope add` — Add a scope (gated)

```bash
export SG_AWS__CREDS__ALLOW_MUTATIONS=1
sg aws creds scope add --name dev --role arn:aws:iam::123456789012:role/Dev
sg aws creds scope add --name prod --role arn:aws:iam::123456789012:role/Prod --max-ttl 30m --yes
sg aws creds scope add --name staging --role arn:aws:iam::1:role/Stg --json
```

`--max-ttl` is the upper bound enforced by `get`. Requests for a longer TTL are rejected.

---

### `scope remove` — Remove a scope (gated)

```bash
export SG_AWS__CREDS__ALLOW_MUTATIONS=1
sg aws creds scope remove dev --yes
```

---

### `scope update` — Update a scope in place (gated)

```bash
export SG_AWS__CREDS__ALLOW_MUTATIONS=1
sg aws creds scope update dev --role arn:aws:iam::1:role/DevV2 --yes
sg aws creds scope update dev --max-ttl 2h --yes
```

---

### `audit list` — Tail the assumption log

```bash
sg aws creds audit list                              # last 1h (default)
sg aws creds audit list --since 24h
sg aws creds audit list --scope prod --since 6h
sg aws creds audit list --caller arn:aws:iam::1:user/alice
sg aws creds audit list --json
```

---

### `audit show` — Show one assumption record

```bash
sg aws creds audit show <assumption_id>
sg aws creds audit show <assumption_id> --json
```

---

## Catalogue and audit log locations

| File | Permissions | Purpose |
|------|-------------|---------|
| `~/.sg/aws/creds/scopes.json` | 0600 | Named scope catalogue (name → role ARN + max-TTL) |
| `~/.sg/aws/creds/audit.jsonl` | 0600 | Append-only assumption log (JSONL) |

Both files are created on first use. They are local to the machine — no remote sync.

---

## Security notes

- **TTL cap:** The requested `--ttl` must be ≤ the scope's `max_ttl`. Exceeding it exits with code 1.
- **No secret in audit log:** `secret_access_key` is never written to disk.
- **0600 permissions:** Both files are owner-readable only.
- **Mutation gate:** Scope catalogue changes require `SG_AWS__CREDS__ALLOW_MUTATIONS=1`.
- **AppSec sign-off:** Required before using this surface in regulated environments.

---

## Backing service classes

| Class | File |
|-------|------|
| `Creds__Scope__Catalogue` | `aws/creds/service/Creds__Scope__Catalogue.py` |
| `Creds__STS__Client` | `aws/creds/service/Creds__STS__Client.py` |
| `Creds__Audit__Log` | `aws/creds/service/Creds__Audit__Log.py` |
| `Creds__TTL__Parser` | `aws/creds/service/Creds__TTL__Parser.py` |
