---
title: "06 — Agent C — CloudFront experiments + sg aws cf expansion (P3)"
file: 06__agent-C__cloudfront-experiments.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
size: L (large) — ~2000 prod lines, ~600 test lines, ~2.5 days
depends_on: Foundation PR
delivers: lab P3 from lab-brief/07 + the sg aws cf primitive expansion (Decision #8)
---

# Agent C — CloudFront experiments + `sg aws cf` expansion

Pairs CloudFront lab experiments with the `sg aws cf` verbs the v2 brief needs. The slowest tier — CF create / delete cycles are ~30 min round-trip — so dev iteration relies heavily on `--dry-run`.

---

## Part 1 — Lab CloudFront experiments

**Folder:** `sgraph_ai_service_playwright__cli/aws/lab/service/experiments/cf/`

**Files to create:**

| File | Tier | Experiment |
|------|------|------------|
| `E20__cf_distribution_inspect.py` | 0 (read-only) | Render a distribution config for humans |
| `E21__cf_edge_locality.py` | 0 | What edge IPs resolve from N positions |
| `E22__cf_tls_handshake.py` | 0 | TLS version, cipher, cert chain |
| `E25__cf_cache_policy_enforcement.py` | 2 (~25 min) | Q3 — does CachingDisabled actually disable caching? |
| `E26__cf_origin_error_handling.py` | 2 (~25 min) | Q3 — parametric `--case {timeout,503,502,refused,slow-headers}` |

Note: **E27** (full-cold-path-end-to-end) is **Agent D's**, not yours — it's the composite that pulls A+B+C together.

**Plus:**
- `service/teardown/Lab__Teardown__CF.py` — full implementation, **including the async disable-pending-delete pattern** (per `02__common-foundation.md §4`). The hard part of this slice.
- `service/teardown/Lab__Teardown__ACM.py` — implementation (lab-minted certs only — **never** delete a shared cert)
- `service/teardown/Lab__Teardown__EC2.py` — stub for E26's "origin pointed at non-existent host" case (lab-tagged only)
- `service/teardown/Lab__Teardown__SSM.py` — stub
- `service/temp_clients/Lab__CloudFront__Client__Temp.py` — boto3 wrapper, tagged for deletion in P-Swap
- `schemas/Schema__Lab__Result__CF__*.py` — one per result shape
- Registration lines in `service/experiments/registry.py` (5 entries)

---

## Part 2 — `sg aws cf` primitive expansion

**Decision #8** folds these into this slice. Five new verbs:

| Verb | Purpose | Used by |
|------|---------|---------|
| `distribution update` | Edit cache behaviour, alias list, origin (without delete-recreate) | E25/E26, v2 brief phase 1 |
| `distribution invalidate` | Create + monitor a cache invalidation | E25 cleanup, v2 brief |
| `distribution origin-group create` | Build CF origin-group (primary + secondary failover) | E26 `--case timeout`, v2 brief phase 2b |
| `distribution tags {list,set,remove}` | Tag management | Lab tagging convention; sweeper |
| `oac {create,list,delete}` | Origin Access Control (for future S3 origins) | v2 brief future hardening |

**Files to create / extend:**

- `aws/cf/cli/verb_distribution_update.py`
- `aws/cf/cli/verb_distribution_invalidate.py`
- `aws/cf/cli/verb_distribution_origin_group.py`
- `aws/cf/cli/verb_distribution_tags.py`
- `aws/cf/cli/verb_oac.py`
- `aws/cf/service/CloudFront__AWS__Client.py` — add `update_distribution`, `create_invalidation`, `get_invalidation`, `list_invalidations`, `create_origin_group_config`, `tag_resource`, `untag_resource`, `list_tags_for_resource`, `create_origin_access_control`, `delete_origin_access_control`, `list_origin_access_controls`
- `aws/cf/service/CloudFront__Distribution__Update__Builder.py` — separate update-config-builder (the existing `Distribution__Builder` is create-only)
- `aws/cf/service/CloudFront__Invalidation__Monitor.py` — poll `get_invalidation` until Completed

Plus matching tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/cf/`.

**Update the user docs** in `library/docs/cli/sg-aws/05__cloudfront.md` — fill out the "Not yet implemented" section into live entries.

---

## What you do NOT touch

- `experiments/dns/`, `experiments/lambda_/`, `experiments/transition/`
- `Lab__Teardown__{R53,Lambda,IAM}.py`
- `aws/dns/` and `aws/lambda_/` packages
- `serve`, `runs diff`, HTML viewer — Agent E
- E27 (full cold-path e2e) — Agent D

---

## Reuse, don't rewrite

| Existing class | Path | Use for |
|---------------|------|---------|
| `CloudFront__AWS__Client` | `aws/cf/service/` | Existing list/get/create/disable/delete/wait. Extend, don't replace. |
| `CloudFront__Distribution__Builder` | `aws/cf/service/` | Create-config builder (existing) |
| `CloudFront__Origin__Failover__Builder` | `aws/cf/service/` | Existing — your `distribution origin-group create` verb uses this |
| `ACM__AWS__Client` | `aws/acm/service/` | For experiments that need cert info |
| Agent B's `lab_error_origin` Lambda | `aws/lab/service/lambdas/` | E26 uses this as the origin |

---

## Risks to watch

- **CF deletion is async.** A failed `delete_distribution` because the distribution is `Enabled` or `In Progress` is the most common harness bug. Your `Lab__Teardown__CF.py` MUST follow the pattern in `02__common-foundation.md §4` — disable, mark `DELETED_PENDING_CF_DISABLE`, queue for next sweep.
- **Cert region.** Every cert used by CF must be in `us-east-1`. If you mint a cert for a lab experiment (don't, if you can reuse one), do it in `us-east-1`.
- **30-minute dev iterations.** Use `--dry-run` heavily. Use existing distributions for E20/E21/E22 development. Reserve the Tier-2 experiments for the final acceptance run.
- **Invalidation costs money.** First 1000/month are free, then $0.005 each. Don't iterate on invalidation logic against real distributions — `Lab__CloudFront__Client__Temp__In_Memory` mocks for unit tests.
- **OAC creation is global-scoped.** OAC objects are CF-global (no region). Lab OACs should be name-prefixed `sg-lab-oac-*` and the sweeper should pick them up.
- **Update verb is the trickiest.** CF's update requires the *full* config object plus an `ETag` — a partial update is not possible. Your `Distribution__Update__Builder` must fetch-then-mutate-then-put.

---

## Acceptance

```bash
sg aws lab list                                       # 5 CF experiments now visible

# read-only — works on existing distributions
sg aws lab run E20 E1ABC2DEF3GHI                      # inspect
sg aws lab run E21 d1234.cloudfront.net               # edge locality
sg aws lab run E22 waker.sg-compute.sgraph.ai         # TLS handshake

# mutating — gated + tier-2
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E25 --tier-2-confirm
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E26 --case timeout --tier-2-confirm

# new sg aws cf verbs
SG_AWS__CF__ALLOW_MUTATIONS=1 sg aws cf distribution update E1ABC2DEF3GHI \
  --add-alias new.example.com
SG_AWS__CF__ALLOW_MUTATIONS=1 sg aws cf distribution invalidate E1ABC2DEF3GHI \
  --paths "/*"
sg aws cf distribution tags list E1ABC2DEF3GHI

# verify clean (note: CF disables may be pending — that's OK)
sg aws lab sweep --pending                            # finish any pending CF deletes
```

Plus:

```bash
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/experiments/cf/ -v
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/cf/ -v
SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1 \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety_cf.py
```

The CF safety integration test is **long** (~45 min) because CF deletes are slow. Document the timeout (`pytest --timeout=3600`).

---

## Commit + PR

Branch: `claude/aws-primitives-support-NVyEh-cf`. Commit prefix: `feat(v0.2.28): lab agent-C — CloudFront experiments + sg aws cf expansion`.

Open PR against `claude/aws-primitives-support-NVyEh`.
