---
title: "sg aws cf — CloudFront distributions"
file: 05__cloudfront.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 05 — `sg aws cf`

CloudFront distribution lifecycle — list, show, create, disable, delete, wait.

**Mutation gate:** `SG_AWS__CF__ALLOW_MUTATIONS=1` required for `create`, `disable`, `delete`.

Subcommand groups:

| Group | What it does |
|-------|--------------|
| `distributions` | Account-wide listing |
| `distribution` | Single-distribution operations |

---

## `distributions list`

Every CloudFront distribution in the account.

```bash
sg aws cf distributions list
sg aws cf distributions list --json
```

---

## `distribution show DIST_ID`

Full details for one distribution — aliases, origin, cache behaviour, cert ARN, status.

```bash
sg aws cf distribution show E1ABC2DEF3GHI
sg aws cf distribution show E1ABC2DEF3GHI --json
```

---

## `distribution create`  ⚠ mutates

Create a new distribution pointing at a Lambda Function URL. The minimum-viable shape today — origin = Function URL, cache = CachingDisabled, one cert.

```bash
SG_AWS__CF__ALLOW_MUTATIONS=1 sg aws cf distribution create \
  --origin-fn-url https://abcd1234.lambda-url.us-west-2.on.aws \
  --cert-arn      arn:aws:acm:us-east-1:123456789012:certificate/xyz \
  --aliases       waker.sg-compute.sgraph.ai \
  --comment       "Waker distribution (created by sg aws cf)"
```

**Flags:**
- `--origin-fn-url URL` (required) — the Lambda Function URL to front
- `--cert-arn ARN` (required) — ACM cert, must be in `us-east-1`
- `--aliases CNAME1,CNAME2` — comma-separated alternate domain names
- `--comment TEXT` — free-text comment stored on the distribution
- `--price-class CLASS` — default `PriceClass_All` (also `PriceClass_100`, `PriceClass_200`)
- `--json`

After creation it takes ~15 min to reach `Deployed`. Use `distribution wait`:

```bash
sg aws cf distribution wait E1ABC2DEF3GHI
```

---

## `distribution disable DIST_ID`  ⚠ mutates

Set `Enabled=false`. Required before deletion. Takes ~15 min for the deactivation to fully propagate (the distribution reaches `Disabled + Deployed`).

```bash
SG_AWS__CF__ALLOW_MUTATIONS=1 sg aws cf distribution disable E1ABC2DEF3GHI
sg aws cf distribution wait    E1ABC2DEF3GHI       # wait for Disabled+Deployed
```

---

## `distribution delete DIST_ID`  ⚠ mutates

Delete a `Disabled + Deployed` distribution. Will fail if it's still enabled or still deploying.

```bash
SG_AWS__CF__ALLOW_MUTATIONS=1 sg aws cf distribution delete E1ABC2DEF3GHI
```

---

## `distribution wait DIST_ID`

Block until the distribution reaches `Deployed` (status). Use after `create` or `disable`.

```bash
sg aws cf distribution wait E1ABC2DEF3GHI
sg aws cf distribution wait E1ABC2DEF3GHI --timeout 1200
```

**Flags:**
- `--timeout N` — seconds to poll (default 900)
- `--json`

---

## End-to-end disable + delete

```bash
# 1. disable
SG_AWS__CF__ALLOW_MUTATIONS=1 sg aws cf distribution disable $DIST
# 2. wait until disabled-and-deployed (~15 min)
sg aws cf distribution wait $DIST
# 3. delete
SG_AWS__CF__ALLOW_MUTATIONS=1 sg aws cf distribution delete $DIST
```

CloudFront is the slowest AWS surface here. Budget 20-30 min for create→deployed→disable→deployed→delete round-trips.

---

## What backs this

Code at `sgraph_ai_service_playwright__cli/aws/cf/`:

| Class | What it does |
|-------|-------------|
| `CloudFront__AWS__Client` | boto3 wrapper — list / get / create / update / delete / `wait_deployed` |
| `CloudFront__Distribution__Builder` | Build the distribution config from request schema |
| `CloudFront__Origin__Failover__Builder` | Build CF origin-group failover configs (used by waker patterns) |

Tests: `tests/unit/sgraph_ai_service_playwright__cli/aws/cf/`.

---

## Not yet implemented

The v0.2.26 surface is intentionally narrow. **PROPOSED** for v0.2.28 (see [`library/dev_packs/v0.2.28__sg-aws-lab-harness/`](../../../dev_packs/v0.2.28__sg-aws-lab-harness/README.md)):

- Custom cache behaviours beyond `CachingDisabled`
- Multi-origin distributions and origin groups via flags (not just builders)
- `update` verb (cache-behaviour edits, alias edits)
- `tags` verb
- Per-distribution invalidation (`distribution invalidate`)
- Origin Access Control (OAC) for S3 origins
