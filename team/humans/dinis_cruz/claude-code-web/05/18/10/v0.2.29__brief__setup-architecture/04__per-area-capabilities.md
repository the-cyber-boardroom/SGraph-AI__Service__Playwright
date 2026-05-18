---
title: "04 — Per-area capabilities"
file: 04__per-area-capabilities.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 04 — Per-area capabilities

For each AWS area we touch in setup, we define the same five verbs:
`create / update / delete / check / status`. Each lives in a
`Setup__{Area}` class under `sg_compute_specs/vault_publish/setup/service/`.

Naming convention: the **verb on the class** matches the operator's
intent (`ensure`, `apply`, `remove`, `check`). The CLI maps the
operator-friendly names (`create`, `update`, `delete`, `check`,
`status`) to those methods.

---

## ACM (certificate)

The wildcard ACM cert MUST live in `us-east-1` (CloudFront requirement)
and MUST cover `*.{zone}` (e.g. `*.aws.sg-labs.app`).

```
sg vault-publish setup acm check     →  Report: present / missing / wrong region / wrong domain
sg vault-publish setup acm status    →  Pretty-print the live cert config
sg vault-publish setup acm create    →  Refuse — ACM cert creation needs DNS validation,
                                        always operator-driven. Prints instructions.
sg vault-publish setup acm update    →  Same as create — no-op, prints instructions.
sg vault-publish setup acm delete    →  Refuse — cert is referenced by CF; safety.
```

**Why ACM is read-only here:** DNS-validated certs require operator
involvement (the validation CNAMEs land outside our zone). We refuse
to wire that into bootstrap. `check` reports presence and correctness
of the cert ARN that the operator passes in.

**Schema:**
```python
class Schema__Setup__ACM__Report(Type_Safe):
    state           : Enum__Setup__State                # OK / MISSING / DRIFT
    cert_arn        : Safe_Str__Cert__Arn               # what we have
    cert_region     : str                                # must be 'us-east-1'
    domain_names    : List__Domain__Name                 # subjects on the cert
    expected_alias  : str                                # f'*.{zone}'
    issues          : List__Setup__Issue                 # human-readable problems
```

---

## CloudFront (distribution)

The CF distribution fronts the cold path. One distribution per zone.
Origin = the Lambda Function URL hostname.

```
sg vault-publish setup cf check      →  Report: present / origin matches / aliases match / cert matches
sg vault-publish setup cf status     →  Pretty-print
sg vault-publish setup cf create     →  Ensure distribution exists for our zone
sg vault-publish setup cf update     →  Apply drift (e.g. origin URL changed)
sg vault-publish setup cf delete     →  Disable + wait + delete (slow; gated)
```

**Identification:** find by Aliases match — if any distribution has
`*.{zone}` in its Aliases, that's ours. Two distributions with the
same alias is a configuration error (CF prevents it on create); we
surface it in `check`.

**The drift cases we detect:**
- Origin domain doesn't match the live Lambda Function URL hostname
  (happens if the Lambda was recreated, which mints a new URL)
- Cert ARN doesn't match the ACM cert
- Caching is enabled (it must be disabled — we cache nothing)
- Aliases list doesn't match the zone

**Schema:**
```python
class Schema__Setup__CF__Report(Type_Safe):
    state            : Enum__Setup__State
    distribution_id  : Safe_Str__CF__Distribution__Id
    domain_name      : Safe_Str__CF__Domain_Name        # the *.cloudfront.net hostname
    origin_domain    : Safe_Str__CF__Domain_Name        # what's in the distribution config
    expected_origin  : Safe_Str__CF__Domain_Name        # what it SHOULD be (live Lambda URL)
    aliases          : List__CF__Alias
    cert_arn         : Safe_Str__Cert__Arn
    enabled          : bool
    deployment_state : str                               # 'Deployed' / 'InProgress'
    issues           : List__Setup__Issue
```

---

## Lambda (function code + config)

The waker Lambda. Code + handler + runtime + memory + timeout.

```
sg vault-publish setup lambda check   →  Report: present / handler matches / runtime matches / role attached
sg vault-publish setup lambda status  →  Pretty-print
sg vault-publish setup lambda create  →  Deploy if missing
sg vault-publish setup lambda update  →  Re-zip + update_function_code + update_function_configuration
sg vault-publish setup lambda delete  →  delete_function (gated)
```

**Drift cases:**
- Handler doesn't match `WAKER_HANDLER`
- Runtime doesn't match `PYTHON_3_12`
- Code SHA256 differs from what we'd upload (this is the
  "re-deploy needed" signal)
- Role ARN doesn't point at our IAM role
- Layers attached / not attached (when we add LWA back, if ever)

**Schema:**
```python
class Schema__Setup__Lambda__Report(Type_Safe):
    state          : Enum__Setup__State
    function_name  : Safe_Str__Lambda__Name
    function_arn   : Safe_Str__Lambda__Arn
    handler        : str
    runtime        : Enum__Lambda__Runtime
    memory_size    : int
    timeout        : int
    role_arn       : Safe_Str__IAM__Role__Arn
    code_sha256    : str
    expected_sha   : str                                  # SHA256 of what we'd upload
    layers         : List__Safe_Str__Layer__Arn
    last_modified  : str
    issues         : List__Setup__Issue
```

---

## Function URL (Lambda URL)

The HTTP endpoint that CloudFront uses as origin. AuthType=NONE.

```
sg vault-publish setup url check      →  Report: present / auth type / public permission
sg vault-publish setup url status     →  Pretty-print URL + auth + permission state
sg vault-publish setup url create     →  Create config + add public InvokeFunctionUrl permission
sg vault-publish setup url update     →  Update auth type if drifted (rare)
sg vault-publish setup url delete     →  Delete URL config (gated)
```

**This is the area that broke today.** Today's `create_function_url`
doesn't check first. `setup url create` checks-then-creates.

**Drift cases:**
- AuthType is not NONE (we use NONE because CF authenticates via OAI
  is not supported for Function URLs — public + tag-based filtering
  on the CF side is our model)
- Statement `FunctionURLAllowPublicAccess` missing from the resource
  policy

**Schema:**
```python
class Schema__Setup__Function_URL__Report(Type_Safe):
    state                  : Enum__Setup__State
    function_name          : Safe_Str__Lambda__Name
    url                    : str                                # https://xxx.lambda-url...
    auth_type              : Enum__Lambda__Url__Auth_Type
    public_invoke_allowed  : bool                               # the resource policy statement
    issues                 : List__Setup__Issue
```

---

## IAM (execution role + policy)

The role the Lambda assumes. Trust policy + execution policy.

```
sg vault-publish setup iam check      →  Report: role exists / trust policy ok / inline policy matches template
sg vault-publish setup iam status     →  Pretty-print role + attached policies
sg vault-publish setup iam create     →  Create role + attach policy from Waker__Policy__Template
sg vault-publish setup iam update     →  Replace inline policy with template (catches drift)
sg vault-publish setup iam delete     →  Detach + delete (gated)
```

**Drift detection is the big win here.** Today, if someone edits the
policy in the console, we have no way to know. `check` compares the
live inline policy JSON to `Waker__Policy__Template().build()` and
reports missing / extra statements.

**Schema:**
```python
class Schema__Setup__IAM__Report(Type_Safe):
    state           : Enum__Setup__State
    role_name       : Safe_Str__IAM__Role__Name
    role_arn        : Safe_Str__IAM__Role__Arn
    trust_policy    : dict                                # parsed
    inline_policies : Dict__Policy__Name__To__Document    # name -> parsed JSON
    expected_policy : Schema__IAM__Policy                 # from Waker__Policy__Template
    missing_stmts   : List__Schema__IAM__Statement        # in expected, not in live
    extra_stmts     : List__Schema__IAM__Statement        # in live, not in expected
    issues          : List__Setup__Issue
```

---

## S3 (Lambda layer bucket — optional, phase B+)

If we adopt the osbot-aws layer-via-S3 approach (currently we don't —
deps are bundled in the zip), we need a bucket for layer uploads.

```
sg vault-publish setup s3 check      →  Report: bucket exists / region correct / versioning
sg vault-publish setup s3 status     →  Pretty-print
sg vault-publish setup s3 create     →  Create bucket if missing
sg vault-publish setup s3 update     →  No-op for now
sg vault-publish setup s3 delete     →  Refuse if not empty
```

**Skip this in phase B if we keep bundling deps in the zip.** The
current waker zip is ~10 MB — well under the 50 MB direct-upload
limit. We only need this area if/when the zip outgrows that.

---

## Route 53 (wildcard ALIAS — setup-only piece)

Per-slug A records are runtime; the wildcard ALIAS `*.{zone}` →
CloudFront is setup.

```
sg vault-publish setup dns check      →  Report: wildcard present / points at our CF
sg vault-publish setup dns status     →  Pretty-print
sg vault-publish setup dns create     →  upsert wildcard ALIAS to CF domain
sg vault-publish setup dns update     →  Re-point if CF distribution domain changed
sg vault-publish setup dns delete     →  Remove wildcard (gated; will break cold path)
```

**Identification:** look up the hosted zone for `{zone}`, then check
the `*.{zone}` ALIAS record's value.

**Drift case:** if the CF distribution was deleted and recreated, its
`*.cloudfront.net` domain changes — wildcard ALIAS needs re-pointing.

**Schema:**
```python
class Schema__Setup__DNS__Report(Type_Safe):
    state            : Enum__Setup__State
    zone             : str
    hosted_zone_id   : str
    wildcard_present : bool
    wildcard_target  : str                              # the CF domain in the ALIAS today
    expected_target  : str                              # the live CF distribution domain
    issues           : List__Setup__Issue
```

---

## Common patterns across all areas

**`check` is read-only.** Never mutates. Safe to run as often as you
want, no `*_ALLOW_MUTATIONS` gate.

**`create` is idempotent.** Runs `check` first internally. If the
resource exists and matches expectations → no-op + log "already
correct". If exists but drift → calls `update`. If missing → creates.

**`update` is the only mutating verb that's not gated.** It applies
the expected config. Use case: "I just changed
`Waker__Policy__Template`, push it to AWS."

Wait — actually `update` mutates too. Gate everything mutating:
`SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1`. One env var for
all setup mutations; matches today's pattern from `SG_AWS__CF__ALLOW_MUTATIONS`.

**`delete` requires a separate, stronger gate.** Probably
`SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1` plus interactive
"type 'delete' to confirm" prompt. Setup deletes are slow to recover.

**Every report includes `issues: List__Setup__Issue`.** A typed list
of "this is what's wrong" entries with severity (`INFO/WARN/ERROR`)
and a one-line description. The `check` command pretty-prints these.

---

## Dependency order

For `bootstrap` (create everything) and `teardown` (delete everything),
the order is fixed by dependencies:

```
                    create order →               ← delete order
                    
ACM            (operator pre-step — check only)
                    │
                    ▼
IAM (role + policy)
                    │
                    ▼
Lambda function (depends on IAM role)
                    │
                    ▼
Function URL    (depends on Lambda function)
                    │
                    ▼
CloudFront      (depends on Function URL + ACM cert)
                    │
                    ▼
Route 53 wildcard ALIAS (depends on CloudFront)
```

`bootstrap` iterates top-down. `teardown` iterates bottom-up. Each
step waits for its dependency to be ready (CF takes 5–15 min to
deploy; that wait happens inside `Setup__CloudFront.create`).
