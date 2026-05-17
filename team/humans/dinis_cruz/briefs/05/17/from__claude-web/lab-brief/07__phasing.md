---
title: "07 — Phasing & dependencies on the v2 brief"
file: 07__phasing.md
author: Architect (Claude)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 07 — Phasing & dependencies

How to land the harness. **The first phase ships in 1–2 days and unlocks immediate measurement value with no dependency on the v2 brief.**

---

## Dependency map vs the v2 brief

```
   v2 brief phasing                                    Lab phasing
   ──────────────                                      ───────────

   Phase 0  validate manually          ←──  needs  ──  none (manual phase)
   Phase 1a stop/start                 ←──  needs  ──  Lab P0 (read-only DNS) very useful for Q2 baselines
   Phase 1b spec scaffold              ←──  needs  ──  Lab P1 (mutating DNS) — proves D3.x before Slug__Registry exists
   Phase 2a sg aws cf                  ──►  enables ──► Lab P3 (CF Tier-2 experiments stop using Temp client)
   Phase 2b sg aws lambda              ──►  enables ──► Lab P2 (Lambda experiments stop using Temp client)
   Phase 2c Waker handler              ←──  needs  ──  Lab P4 (full E27 e2e) gives confidence in the design
   Phase 2d wire bootstrap             ←──  needs  ──  Lab E27 acts as bootstrap-acceptance-smoke
```

Two key observations:

1. **Lab P0 + P1 (DNS-only) can ship before any v2 phase.** The biggest assumption in v2 (Q1, Q2) is the DNS specific-beats-wildcard claim — and that's testable today with just `Route53__AWS__Client`. We can run E10 / E11 / E12 / E13 / E14 against a real zone tomorrow.
2. **The lab uses Temp clients for CF/Lambda until v2 phase 2a/2b lands.** Those Temp clients are deleted on a swap commit once the real `sg aws cf` / `sg aws lambda` arrive. The harness's *behaviour* doesn't change; only the import line.

This makes the harness valuable **before** v2 has shipped a single line of new code — which is the strongest argument for landing it first.

---

## Phasing

### Phase P0 — DNS read-only experiments (SMALL)

**Goal:** scaffold the harness; ship 4 read-only experiments. No mutations. Establishes the harness shape end-to-end.

**Scope:**
- Folder skeleton per [`05 §1`](05__module-layout.md#1-folder)
- `Lab__Runner`, `Lab__Ledger`, `Lab__Timing`, `Lab__Safety__Account_Guard`, `Lab__Tagger`
- `Render__Table`, `Render__JSON`
- Experiments E01, E02, E03, E04
- CLI: `sg aws lab list`, `sg aws lab show`, `sg aws lab run`, `sg aws lab runs list/show`, `sg aws lab account show`
- No mutating teardown infra yet — read-only doesn't need it. Ledger and `Lab__Sweeper` are stubbed.
- Unit tests + ~~integration tests for read-only experiments against the real zone~~ (gated, but no AWS *mutations*, so safe)

**Acceptance:**
```bash
sg aws lab account show                          # shows AWS account + region + caller
sg aws lab list                                  # 4 experiments visible
sg aws lab run E01 --zone sg-compute.sgraph.ai   # rendered table
sg aws lab run E02 google.com                    # 8 resolvers, latency table
```

**Owner:** Dev. Size: ~1 day.

---

### Phase P1 — DNS mutating experiments + the safety story (MEDIUM)

**Goal:** the **value-rich** phase. Adds the ledger, sweeper, teardown dispatcher, and the 5 DNS-mutating experiments. After this phase, we have **real propagation numbers**.

**Scope:**
- `Lab__Ledger` for real (JSONL writer + reader + lock)
- `Lab__Sweeper` (tag-driven discovery + delete)
- `Lab__Teardown__Dispatcher` + `Lab__Teardown__R53`
- atexit + signal handlers wired in `Lab__Runner.start`
- `Render__Timeline__ASCII`
- Experiments E10, E11, E12, E13, E14
- `Schema__Lab__Result__DNS__Propagation` and friends
- `sg aws lab sweep` CLI verb
- `SG_AWS__LAB__ALLOW_MUTATIONS=1` gate
- Integration test: the kill-9 safety acceptance test from [`04 §8`](04__safety-and-cleanup.md#8-the-acceptance-test-for-the-safety-story) **restricted to DNS-only** (no CF yet)

**Acceptance:**
```bash
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E11 --ttl 60
# Outputs the propagation table + timeline + cleans up.
sg aws lab sweep                                 # → "no leaked resources"
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E12  # wildcard-vs-specific against the real zone
# After: Q1 and Q2 (from §1) have measured answers.
```

**Risk to watch:** Route 53 mutations rate-limit — 5 per second per zone. E10 (repeat 20) needs throttling. Build a `Rate__Limiter__Token__Bucket` for Route 53 calls (~30 lines).

**Owner:** Dev. Size: ~2 days.

---

### Phase P2 — Lambda experiments (MEDIUM)

**Goal:** the Lambda half. Adds `Lab__CloudFront__Client__Temp` + the in-tree lab Lambda functions; ships 6 Lambda experiments.

**Scope:**
- `Lab__CloudFront__Client__Temp` (boto3 wrapper — to be deleted later)
- `Lab__Lambda__Client__Temp` (boto3 wrapper — to be deleted later)
- `Lab__Teardown__Lambda`, `Lab__Teardown__IAM`
- The three in-tree lab Lambda functions (`lab_waker_stub`, `lab_error_origin`, `lab_internal_caller`) packaged via `osbot_aws.Deploy_Lambda`
- Experiments E30, E31, E32, E33, E34, E35
- `Render__Histogram__ASCII` for cold-start distributions

**Acceptance:**
```bash
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E30 --repeat 20
# 20 cold-starts measured + histogram + p50/p99
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E32 --body-size 1MB,5MB,9MB
# Concrete numbers on BUFFERED vs RESPONSE_STREAM
# After this run: review item #1 (streaming) is answered with data, not opinion.
```

**Owner:** Dev. Size: ~2 days.

---

### Phase P3 — CloudFront experiments (MEDIUM)

**Goal:** the slowest tier. Adds CloudFront Tier-0 experiments (E20-E22 cheap) and the Tier-2 ones (E25, E26).

**Scope:**
- `Lab__Teardown__CF` + the pending-deletes queue
- `Lab__Teardown__ACM` (only if any lab-minted cert)
- Experiments E20, E21, E22, E25, E26
- `Render__Table` extended for CF result shapes

**Acceptance:**
```bash
sg aws lab run E20 <existing-distribution-id>          # read-only inspect (Tier 0)
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E25      # ~25 min — proves CachingDisabled enforcement
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E26 --case timeout
# Concrete numbers on CF behaviour under origin timeout
```

**Risk to watch:** CF distribution create/delete cycles. Each is ~30 min round-trip. Budget the experiment runtimes generously; encourage `--dry-run` for development.

**Owner:** Dev. Size: ~2 days.

---

### Phase P4 — Transition / composite experiments + E27 (MEDIUM)

**Goal:** the experiments that prove the *system*, not just primitives.

**Scope:**
- Experiments E27, E40, E41, E42
- The waterfall diagram in `Render__Timeline__ASCII` (richer for E27)

**Acceptance:**
```bash
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E40
# DNS-swap window measured per-resolver
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E27 --tier-2-confirm
# Full cold-path waterfall; the v2 architecture's biggest claim, measured.
```

After P4, we have **measured answers to all 5 questions** in [§1](01__intent-and-principles.md#1-the-five-questions-the-v2-brief-assumes-are-answered). The v2 brief can move to Dev with empirical backing.

**Owner:** Dev. Size: ~1.5 days.

---

### Phase P5 — UI viewer + diff (SMALL)

**Goal:** the HTML viewer + the runs-diff feature.

**Scope:**
- `sg aws lab serve` — FastAPI app reading `.sg-lab/runs/`
- `sg aws lab runs diff` — schema-walking diff with sign/Δ rendering
- The architecture diagrams from [`06 §2`](06__ui-and-visualisation.md#2-the-flow-diagram-artefacts)

**Acceptance:**
```bash
sg aws lab serve --port 8090
# → open http://localhost:8090/runs/ in browser, navigate past runs
sg aws lab runs diff <run-A> <run-B>
# → side-by-side terminal rendering
```

**Owner:** Dev. Size: ~1 day.

---

### Phase P-Swap — Replace Temp clients (SMALL)

Triggered when v2 phase 2a (`sg aws cf`) and 2b (`sg aws lambda`) land. A single PR:

- Delete `Lab__CloudFront__Client__Temp`
- Delete `Lab__Lambda__Client__Temp`
- Replace imports across `experiments/cf/` and `experiments/lambda_/` with the new primitives
- All tests still pass (same surface, different implementation)

**Owner:** Dev. Size: ~0.5 days (mostly a sed + run-the-tests).

---

## Critical path

```
P0 ─────► P1 ─────► P2 ───┐
                          │
                          ├─────► P4 ─────► P-Swap (gated on v2 phase 2a/2b)
                          │
                  P3 ─────┘

P5 can land at any time after P0.
```

P1 unlocks the bulk of the value. Get it landed; pull P2 / P3 in parallel if Dev capacity exists; P4 closes the loop.

---

## Cancel points

This is intentionally easy to ship-and-stop at any phase. The cancel-points and their value:

| Stop after | Value delivered |
|------------|-----------------|
| P0 | Discovery + introspection of any zone, free. 8-resolver latency baseline. |
| P1 | **Q1 + Q2 answered with measurements.** The biggest architecture assumption is validated. |
| P2 | Q4 + parts of Q5 answered. The streaming-vs-buffered debate is settled with numbers. |
| P3 | Q3 (CF behaviour) measured. The `CachingDisabled` and origin-error contracts are known. |
| P4 | E27 — the whole v2 cold path measured end-to-end. Q5 fully answered. |
| P5 | Pretty viewer. Optional. |

**The recommendation is: land P0 + P1 in one developer-week, then re-prioritise.** That gives the v2 brief's load-bearing claim a measurement-backed answer before any v2 Dev work starts.

---

## What lands when v2 phase 2 ships

When `sg aws cf` + `sg aws lambda` land (the v2 brief's biggest pieces), the harness's two Temp clients are deleted. The harness then **runs through the new primitives** — and any behavioural change in the new primitives shows up as a diff in lab run results.

That is, the lab also acts as a **regression-detection harness for `sg aws cf` and `sg aws lambda`**. If a CF distribution-config-builder bug slips in, E25 catches it. If Lambda deployment changes cold-start by 50 ms, E30 catches it. The same experiments that proved AWS behaviour also prove our wrappers haven't broken.

This is the second reason to land the harness early — it becomes the regression harness for the work it informed.
