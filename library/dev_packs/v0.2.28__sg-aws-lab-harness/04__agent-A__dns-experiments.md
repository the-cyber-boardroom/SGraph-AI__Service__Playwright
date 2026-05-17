---
title: "04 — Agent A — DNS experiments (P0+P1)"
file: 04__agent-A__dns-experiments.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
size: S (small) — ~900 prod lines, ~500 test lines, ~2 days
depends_on: Foundation PR (02__common-foundation.md)
delivers: lab P0 + lab P1 from lab-brief/07
---

# Agent A — DNS experiments

The smallest slice. The most valuable slice. Lands answers to Q1 + Q2 (the v2 brief's two biggest claims).

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/lab/service/experiments/dns/`

**Files to create** (per `lab-brief/05 §1`):

| File | Tier | Experiment |
|------|------|------------|
| `E01__zone_inventory.py` | 0 (read-only) | Show NS set, record counts, existing wildcards |
| `E02__resolver_latency.py` | 0 | 8-public-resolver dig latency baseline |
| `E03__authoritative_ns_latency.py` | 0 | Per-NS SOA latency |
| `E04__wildcard_pre_check.py` | 0 | What resolvers return for a not-yet-created name |
| `E10__insync_distribution.py` | 1 (mutating-low) | Q2 — `ChangeInfo` PENDING→INSYNC distribution |
| `E11__propagation_timeline.py` | 1 | Q2+Q1 — per-resolver first-correct time after INSYNC |
| `E12__wildcard_vs_specific.py` | 1 | Q1 — specific-record-beats-wildcard |
| `E13__ttl_respect.py` | 1 | Do public resolvers respect declared TTL? |
| `E14__delete_propagation.py` | 1 | How long after `delete_record` do resolvers return NXDOMAIN? |

**Plus:**
- `service/teardown/Lab__Teardown__R53.py` — full implementation (delete record-set with idempotency)
- `schemas/Schema__Lab__Result__DNS__*.py` — one file per result shape (~6 files)
- `service/renderers/Render__Timeline__ASCII.py` — fill in the `render_event_list(...)` body (foundation ships the stub)
- `service/Rate__Limiter__Token__Bucket.py` — Route 53 mutations rate-limit at 5/s/zone; ~30 lines
- Registration lines in `service/experiments/registry.py` (9 entries)

---

## What you do NOT touch

- Any file under `experiments/cf/`, `experiments/lambda_/`, `experiments/transition/`
- `Lab__Teardown__{CF,Lambda,ACM,EC2,SSM,IAM}.py` — those stay stubbed (other agents fill in)
- `aws/cf/` and `aws/lambda_/` packages — DNS primitive expansion is **not** in scope for this slice
- The `serve`, `runs diff`, HTML viewer — those are Agent E

---

## Reuse, don't rewrite

The repo already has every DNS primitive you need. **Reuse them.** New code is the experiments, the result schemas, the renderer, and the ledger glue.

| Existing class | Path | Use for |
|---------------|------|---------|
| `Route53__AWS__Client` | `aws/dns/service/` | upsert_record, delete_record, get_change, list_resource_record_sets |
| `Route53__Authoritative__Checker` | `aws/dns/service/` | `dig +norecurse @<R53 NS>` queries |
| `Route53__Public_Resolver__Checker` | `aws/dns/service/` | 8-resolver fan-out |
| `Route53__Smart_Verify` | `aws/dns/service/` | Post-mutation verification orchestrator |
| `Dig__Runner` | `aws/dns/service/` | `dig` subprocess wrapper |

---

## Acceptance

Run from a fresh checkout of the integration branch with the Foundation PR merged:

```bash
# read-only — no env vars
sg aws lab list                                       # 9 DNS experiments visible
sg aws lab run E01 --zone sg-compute.sgraph.ai        # zone inventory table
sg aws lab run E02 google.com                         # resolver-latency table
sg aws lab run E03 sg-compute.sgraph.ai               # authoritative NS latency
sg aws lab run E04 not-yet-created.sg-compute.sgraph.ai

# mutating
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E10 --repeat 5         # INSYNC distribution
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E11 --ttl 60           # propagation timeline
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E12                    # wildcard-vs-specific
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E14                    # delete propagation

# verify clean
sg aws lab sweep                                      # → "no leaked resources"
```

**Plus** unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/lab/experiments/dns/` pass:

```bash
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/experiments/dns/ -v
```

**Plus** the safety acceptance (DNS-scoped slice of `lab-brief/04 §8`):

```bash
SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1 \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety_dns.py
```

---

## Risks to watch

- **Rate limits.** Route 53 mutations cap at 5/s/zone. Your `Rate__Limiter__Token__Bucket` must be honoured by every mutation in your experiments. E10 `--repeat 20` is the failure case if you don't.
- **TEST-NET enforcement.** Every A-record VALUE you write must be in `192.0.2.0/24`, `198.51.100.0/24`, or `203.0.113.0/24` unless the caller passed `--force-real-ip`. `Lab__Runner.create_and_register(...)` should refuse a non-TEST-NET value.
- **Wildcard interference.** E12 (`wildcard-vs-specific`) might run in a zone where another wildcard already exists. Detect this, refuse to overwrite a non-lab wildcard, and document `--wildcard-already-present` in the CLI help.
- **Public-resolver cache pollution.** E11/E12 spray TEST-NET addresses into public resolver caches. That's the point. Use unique per-run record names (`lab-prop-<run-id>.<zone>`) so no two runs collide.

---

## Commit + PR

Branch: `claude/aws-primitives-support-NVyEh-dns`

Commit messages follow the repo style — `feat(v0.2.28): lab agent-A — DNS experiments (P0+P1)`. Bullet the experiments shipped + the kill-9 result.

Open PR against `claude/aws-primitives-support-NVyEh` (integration branch). Tag the Opus coordinator. Do **not** merge yourself.
