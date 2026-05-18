---
title: "SSM Usage Audit — vault-publish"
file: README.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 11)
triggered-by: "I think we are using it in places we shouldn't"
---

# SSM Usage Audit — vault-publish

A complete inventory of every SSM read and write in the vault-publish
workflow, with a verdict on each: **correct**, **unnecessary**, or
**wrong**.

---

## 1. What uses SSM today

### 1a. `Slug__Registry` — the per-slug data store

**Path pattern:** `/sg-compute/vault-publish/slugs/{slug}`

**Written by:** `Vault_Publish__Service.register()` via
`Slug__Registry.put(slug, vault_key, stack_name, fqdn, region)`.

**JSON payload stored:**
```json
{
  "slug"       : "sara-cv",
  "vault_key"  : "x9k3m2...",
  "stack_name" : "sara-cv",
  "fqdn"       : "sara-cv.aws.sg-labs.app",
  "region"     : "eu-west-2",
  "created_at" : "2026-05-18T11:00:00Z"
}
```

**Read by:**

| Caller | Why |
|--------|-----|
| `Endpoint__Resolver__EC2.resolve()` | Lambda waker — resolve slug → EC2 region + stack_name |
| `Vault_Publish__Service.status()` | CLI — show state of a slug |
| `Vault_Publish__Service.unpublish()` | CLI — get region + stack_name before deleting |
| `Vault_Publish__Service.list_slugs()` | CLI — enumerate all slugs |
| `Slug__Routing__Lookup` | CLI route hints |

**Deleted by:** `Slug__Registry.delete()` during `unpublish`.

**SSM parameter type:** `String` (plaintext) — via `osbot_aws.helpers.Parameter.put()`.

---

### 1b. IAM policy grants to the waker Lambda

```
ssm:GetParameter  on  arn:aws:ssm:*:*:parameter/sg-compute/vault-publish/*
```

The waker can read any parameter under the slug prefix, from any region,
in any account. It cannot write, describe, or delete.

---

## 2. Verdict on each usage

### 2a. `vault_key` in SSM — **WRONG**

The `vault_key` is stored as part of the plaintext JSON blob.
`osbot_aws.helpers.Parameter.put()` defaults to `Type='String'` (cleartext).

**Why this is wrong:**

1. `vault_key` is a secret. Storing it in a plaintext SSM parameter means
   it is visible in the AWS Console, in CloudTrail `PutParameter` events,
   and to anyone with `ssm:GetParameter` on the path.
2. The waker Lambda **never uses `vault_key`**. `Endpoint__Resolver__EC2.resolve()`
   reads only `entry.region` and `entry.stack_name` from the SSM entry.
   The vault_key lives in SSM entirely unused by the Lambda path.
3. The CLI operators who need the vault_key already have it in their local
   keyring (it was passed to `register` by the operator). There is no
   server-side consumer that needs it from SSM.

**What should happen instead:**

Option A (recommended): **Remove `vault_key` from the SSM entry entirely.**
The operator stored it locally at register time. If they need to retrieve
it later, the CLI reads from the local keyring, not from SSM. The SSM entry
carries only the routing metadata the Lambda needs: `slug`, `stack_name`,
`fqdn`, `region`, `created_at`.

Option B (if server-side storage is genuinely needed): **Use
`put_secret()` (SecureString)** and store the vault_key in a separate
dedicated parameter at `/sg-compute/vault-publish/keys/{slug}` with a
narrower IAM policy. The waker role must NOT have `GetParameter` on
that path — only the operator CLI should.

---

### 2b. SSM read on every Lambda invocation — **UNNECESSARY OVERHEAD**

`Endpoint__Resolver__EC2.resolve()` calls `Slug__Registry.get(slug)` which
calls `ssm.get_parameter(Name=...)` on every single request.

For a Lambda that stays warm for minutes-to-hours, this means hundreds
of identical SSM reads for the same slug. Each read:
- Adds ~10–30 ms to the response time
- Costs $0.05 / 10 000 API calls (minor but non-zero)
- Is an unnecessary dependency on SSM availability

**What should happen instead:**

Cache the slug entry in Lambda module-level memory with a short TTL
(e.g., 60 seconds). The entry changes only on `register` or `unpublish`,
which happen via the CLI — not during normal waker operation.

```python
import time

_SLUG_CACHE: dict = {}           # {slug: (entry, cached_at)}
_CACHE_TTL  = 60                 # seconds

def _cached_get(registry, slug: str):
    now = time.time()
    if slug in _SLUG_CACHE:
        entry, ts = _SLUG_CACHE[slug]
        if now - ts < _CACHE_TTL:
            return entry
    entry = registry.get(slug)
    if entry is not None:
        _SLUG_CACHE[slug] = (entry, now)
    return entry
```

A 60-second TTL means: after an `unpublish`, the waker serves one last
warming page for up to 60 seconds before recognising the slug is gone.
That is acceptable — the EC2 is being deleted anyway.

---

### 2c. SSM as the slug registry — **CORRECT**

Using SSM Parameter Store for per-slug routing metadata is the right
decision for this scale. The brief's decision to keep SSM over DynamoDB
or other stores stands:

- No new infrastructure (SSM is already in use and granted)
- Slug count: expected tens, maybe low hundreds — never millions
- `GetParameter` by exact name is O(1) and fast
- Parameters survive Lambda restarts, EC2 restarts, and partial failures
- The operator CLI has full visibility via `describe_parameters`

The only caveat is the caching point above (§2b).

---

### 2d. IAM policy scope — **TOO BROAD (minor)**

Current policy:
```
ssm:GetParameter  on  arn:aws:ssm:*:*:parameter/sg-compute/vault-publish/*
```

This allows the Lambda to read from *any region* and *any account*.

**What it should be:**
```
ssm:GetParameter  on  arn:aws:ssm:{region}:{account_id}:parameter/sg-compute/vault-publish/*
```

Tightening the ARN means a compromised Lambda in one account cannot read
slug registries from other accounts. Low practical risk today (single
account, single region), but worth fixing before expanding.

The waker already knows its own region (env var `AWS_DEFAULT_REGION`) and
account ID (available from the Lambda execution context). These can be
substituted at deploy time or read dynamically.

---

## 3. Summary table

| Usage | Verdict | Action |
|-------|---------|--------|
| SSM as per-slug registry store | ✓ Correct | Keep |
| `stack_name`, `fqdn`, `region` in SSM entry | ✓ Correct | Keep |
| `vault_key` in SSM entry | ✗ Wrong | Remove from SSM entry; keep in local keyring only |
| SSM read on every Lambda invocation | ⚠ Unnecessary overhead | Add 60-second module-level cache |
| SSM parameter type = String (plaintext) | ✗ Wrong | Change to SecureString if vault_key stays (see §2a) |
| IAM policy resource `arn:aws:ssm:*:*:...` | ⚠ Too broad | Tighten to `{region}:{account}` at deploy time |

---

## 4. Recommended changes (ordered by risk)

### Phase A — no breaking changes (do first)
1. **Remove `vault_key` from `Slug__Registry.put()` payload.** The field is
   never read by the Lambda. Existing entries (if any) can be silently
   ignored — `Slug__Registry.get()` already uses `.get('vault_key', '')`
   so the field becoming absent doesn't break anything.
2. **Add 60-second module-level cache** in `Endpoint__Resolver__EC2`.

### Phase B — tighten IAM (do with Phase B3)
3. **Narrow the SSM ARN** in `Waker__Policy__Template` to include region
   and account ID. This requires the bootstrap step to know the account ID
   (it does — it's available from the Lambda context / STS).

### Phase C — if vault_key server-side storage is ever needed
4. If a future feature genuinely needs the vault_key on the server side
   (e.g., a vault_key rotation flow), store it at a separate SSM path
   as SecureString with its own narrower IAM policy, completely separate
   from the routing entry.

---

## 5. Files affected

| File | Change |
|------|--------|
| `sg_compute_specs/vault_publish/service/Slug__Registry.py` | Remove `vault_key` from `put()` payload; add cache helper |
| `sg_compute_specs/vault_publish/waker/Endpoint__Resolver__EC2.py` | Use cached `_cached_get()` |
| `sgraph_ai_service_playwright__cli/aws/iam/service/templates/Waker__Policy__Template.py` | Tighten SSM ARN (Phase B3) |
| `sg_compute_specs/vault_publish/schemas/Schema__Vault_Publish__Entry.py` | Remove `vault_key` field or mark it as not-persisted |

---

## Cross-references

- Decoupling brief → `11/v0.2.29__brief__decoupling-and-eval-cli/`
- Waker internals brief → `10/v0.2.29__brief__waker-internals-ux-debug/`
- Setup architecture brief → `10/v0.2.29__brief__setup-architecture/`
