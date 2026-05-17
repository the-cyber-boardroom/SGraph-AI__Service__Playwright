---
title: "06 — Agent C — CloudFront experiments (P3)"
file: 06__agent-C__cloudfront-experiments.md
author: Architect (Claude)
date: 2026-05-17 (rev 2)
parent: README.md
size: M (medium) — ~1200 prod lines, ~400 test lines, ~2 days
depends_on: Foundation PR + v2 vault-publish phase 2a (sg aws cf expansion)
mandatory_reading:
  - team/humans/dinis_cruz/claude-code-web/05/17/00/v0.2.23__plan__vault-publish-spec/03__delta-from-lab-brief.md  # §B.1 — §B.7
delivers: lab P3 from lab-brief/07
---

# Agent C — CloudFront experiments

Lab CloudFront experiments composed on top of the **v2 vault-publish-shipped `sg aws cf` expansion**. The slowest tier — CF create/delete cycles are ~30 min round-trip — so dev iteration relies heavily on `--dry-run`.

---

## Sequencing — DO NOT START EARLY

This slice **cannot ship before v2 vault-publish phase 2a lands**. Phase 2a is where the `sg aws cf {distribution update, distribution invalidate, distribution origin-group, distribution tags, oac}` verbs (and the matching `CloudFront__AWS__Client` extensions) are added. Rev 2 explicitly dropped the temp-boto3-wrapper fallback (decision #2).

The Opus coordinator fires Agent C **only after v2 phase 2a merges to `dev`** and the integration branch has been rebased onto it.

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/lab/service/experiments/cf/`

**Files to create** (per delta `B.3` — file names match class names, no `E20__` prefix):

| File | Tier | Experiment |
|------|------|------------|
| `Lab__Experiment__CF__Distribution_Inspect.py` | 0 (read-only) | Render a distribution config for humans |
| `Lab__Experiment__CF__Edge_Locality.py` | 0 | What edge IPs resolve from N positions |
| `Lab__Experiment__CF__TLS_Handshake.py` | 0 | TLS version, cipher, cert chain |
| `Lab__Experiment__CF__Cache_Policy_Enforcement.py` | 2 (~25 min) | Q3 — does `CachingDisabled` actually disable caching? |
| `Lab__Experiment__CF__Origin_Error_Handling.py` | 2 (~25 min) | Q3 — parametric `--case {timeout,503,502,refused,slow-headers}` |

Note: **E27** (full-cold-path-end-to-end) is **Agent D's**, not yours — it's the composite that pulls A+B+C together.

**Plus:**
- `service/teardown/Lab__Teardown__CF.py` — full implementation, **including the async disable-pending-delete pattern** (per `02__common-foundation.md §4`). The hard part of this slice. Uses `CloudFront__AWS__Client` directly (v2 phase 2a's update / disable / delete / wait surface).
- `service/teardown/Lab__Teardown__ACM.py` — implementation (lab-minted certs only — **never** delete a shared cert). Uses `ACM__AWS__Client`.
- `service/teardown/Lab__Teardown__EC2.py` — implementation for E26's "origin pointed at non-existent host" case (lab-tagged only)
- `service/teardown/Lab__Teardown__SSM.py` — implementation
- `schemas/Schema__Lab__Result__CF__*.py` — one per result shape. **Per delta `B.1` and `B.4`**: typed collections, no `Dict__Str__Str`.
- Registration lines in `service/experiments/registry.py` (5 entries)

**Experiment-class shape — per delta `B.2`:** runner injected at `setup`, not per-call. (Same pattern as Agent A's example.)

---

## What you do NOT touch

- `experiments/dns/`, `experiments/lambda_/`, `experiments/transition/`
- `Lab__Teardown__{R53,Lambda,IAM}.py`
- **`aws/cf/` package** — NO primitive expansion in this PR. The expansion (`distribution update`, `distribution invalidate`, `distribution origin-group`, `distribution tags`, `oac`) is owned by v2 vault-publish phase 2a. If you find you need a verb that doesn't exist there yet, **stop and escalate**.
- `aws/dns/` and `aws/lambda_/` packages
- `serve`, `runs diff`, HTML viewer — Agent E
- E27 (full cold-path e2e) — Agent D

---

## Reuse, don't rewrite

| Existing class | Path | Use for |
|---------------|------|---------|
| `CloudFront__AWS__Client` | `aws/cf/service/` | **Today's baseline**: list / get / create / disable / delete / `wait_deployed`. The underlying boto3 `update_distribution` call is already invoked internally (inside `disable_distribution`), but is not yet exposed as a public general-purpose update method. **By the time you start**, v2 phase 2a will have exposed `update_distribution` / `create_invalidation` / `get_invalidation` / `list_invalidations` / `create_origin_group_config` / `tag_resource` / OAC verbs as public methods. |
| `CloudFront__Distribution__Builder` | `aws/cf/service/` | Create-config builder (existing) |
| `CloudFront__Origin__Failover__Builder` | `aws/cf/service/` | Existing — used for origin-group experiments |
| `ACM__AWS__Client` | `aws/acm/service/` | For experiments that need cert info; for the rare per-run lab cert |
| `Sg__Aws__Session` | `credentials/service/` | The AWS-client seam |
| Agent B's `lab_error_origin` Lambda | `aws/lab/service/lambdas/` | E26 uses this as the origin (needs B merged first ↑↑↑ which means C effectively waits for B too in the integration branch — note the implicit dependency) |

---

## Risks to watch

- **CF deletion is async.** A failed `delete_distribution` because the distribution is `Enabled` or `In Progress` is the most common harness bug. Your `Lab__Teardown__CF.py` MUST follow the pattern in `02__common-foundation.md §4` — disable, mark `DELETED_PENDING_CF_DISABLE`, queue for next sweep.
- **Cert region.** Every cert used by CF must be in `us-east-1`. Post-v2, the lab uses a dedicated `lab.sg-labs.app` zone with its own wildcard cert (per Q4 RESOLVED). Pre-lab-zone, use the shared lab cert provisioned via the v2-shipped `sg aws acm` expansion.
- **30-minute dev iterations.** Use `--dry-run` heavily. Use existing distributions for E20/E21/E22 development. Reserve the Tier-2 experiments for the final acceptance run.
- **Invalidation costs money.** First 1000/month are free, then $0.005 each. Don't iterate on invalidation logic against real distributions — `CloudFront__AWS__Client__In_Memory` for unit tests.
- **OAC creation is global-scoped.** OAC objects are CF-global (no region). Lab OACs should be name-prefixed `sg-lab-oac-*` and the sweeper should pick them up.
- **Implicit dependency on Agent B's `lab_error_origin` Lambda** for E26. Document in the PR description. If Agent B is still in flight, write E20/E21/E22 first (read-only) and stub E25/E26 with `skip("waits for lab_error_origin")` markers.

---

## Acceptance

```bash
sg aws lab list                                                                # 5 CF experiments now visible

# read-only — works on existing distributions
sg aws lab run cf-distribution-inspect E1ABC2DEF3GHI
sg aws lab run cf-edge-locality        d1234.cloudfront.net
sg aws lab run cf-tls-handshake        waker.sg-compute.sgraph.ai

# mutating — gated + tier-2
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run cf-cache-policy-enforcement --tier-2-confirm
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run cf-origin-error-handling --case timeout --tier-2-confirm

# verify clean (note: CF disables may be pending — that's OK)
sg aws lab sweep --pending                                                     # finish any pending CF deletes

# unit + safety integration
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/experiments/cf/ -v
SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1 \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety_cf.py --timeout=3600
```

The CF safety integration test is **long** (~45 min) because CF deletes are slow. Document the timeout.

---

## Commit + PR

Branch: `claude/aws-primitives-support-NVyEh-cf`. Commit prefix: `feat(v0.3.0): lab agent-C — CloudFront experiments`.

Open PR against `claude/aws-primitives-support-NVyEh`.
