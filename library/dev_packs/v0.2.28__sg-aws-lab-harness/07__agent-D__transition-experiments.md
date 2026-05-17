---
title: "07 — Agent D — Composite transition experiments (P4)"
file: 07__agent-D__transition-experiments.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
size: M (medium) — ~1100 prod lines, ~400 test lines, ~1.5 days
depends_on: Foundation PR + Agent A + Agent B + Agent C (or their temp clients)
delivers: lab P4 from lab-brief/07
---

# Agent D — Composite transition experiments

The slice that proves the **system**, not the primitives. Four experiments that compose A+B+C work into measurements of the v2 brief's biggest claim.

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/lab/service/experiments/transition/`

**Files to create:**

| File | Tier | Experiment |
|------|------|------------|
| `E40__dns_swap_window.py` | 1 | T2 — how long after upserting specific does the resolver still return wildcard |
| `E41__stop_race_window.py` | 1 | T3 — stop-then-delete vs delete-then-stop race |
| `E42__concurrent_cold_thunder.py` | 2 (~10 min) | When N concurrent users hit a cold slug, does the Waker race? Duplicate StartInstances? |
| `E27__full_cold_path_end_to_end.py` | 2 (~30-45 min) | The whole cold path waterfall — the v2 brief's biggest claim measured |

(Note: E27 is *also* a CloudFront-flavoured experiment per `lab-brief/03`, but lives in `experiments/transition/` because it's the composite. Agent C owns the CF-primitive-only experiments.)

**Plus:**
- `service/renderers/Render__Timeline__ASCII.py` — **extend** with `render_waterfall(...)` method (E27's display). Don't edit Agent A's `render_event_list` — add a new method.
- `schemas/Schema__Lab__Result__Transition__*.py` — one per result shape (4 schemas)
- Registration lines in `service/experiments/registry.py` (4 entries)

---

## What you do NOT touch

- Any existing experiment file in `experiments/{dns,cf,lambda_}/` — those are A/B/C's work; you compose with them via the runner
- Any `Lab__Teardown__*.py` — those are owned by A/B/C; you orchestrate, you don't tear down
- `serve`, `runs diff`, HTML viewer — Agent E
- The `aws/cf/` and `aws/lambda_/` primitive packages — those are B+C's expansion territory

---

## How to compose

Each transition experiment is built by **calling the existing experiments in sequence** — not by re-implementing their primitives. The pattern:

```python
class E40__Dns_Swap_Window(Lab__Experiment):
    def execute(self, runner: 'Lab__Runner') -> Schema__Lab__Run__Result:
        # 1. Use Agent A's helpers
        baseline = E11__Propagation_Timeline().execute(runner)

        # 2. Trigger the specific-record upsert
        record_id = runner.create_and_register(
            resource_type   = Enum__Lab__Resource_Type.R53_RECORD,
            factory         = lambda: runner.r53().upsert_record(...),
            cleanup_payload = {...},
            teardown_order  = 30,
        )

        # 3. Use Agent A's resolver fan-out
        observations = runner.public_resolver_checker().observe_until_flip(...)

        return Schema__Lab__Result__Transition__DNS_Swap(
            nominal_ttl                = 60,
            per_resolver_flip_seconds  = observations,
            max_flip_seconds           = max(observations.values()),
        )
```

You **never** call boto3, dig, or the temp clients directly. Everything is through `runner.*()` accessors.

---

## Timing of your slice

You have two start-time options:

| Option | Trade-off |
|--------|-----------|
| **Start when A+B+C merge into integration** (recommended) | Cleanest. You use the real primitives. E27 is straightforward. |
| **Start in parallel with B+C as soon as A merges** | E40+E41 are DNS-only and don't need B+C. You write them first, gate E27/E42 on B+C arrival. |

The Architect's recommendation is to **wait** — your slice is small and lands fast once you have the working primitives. Don't fight merge conflicts in B/C's renderers and runner client accessors.

---

## Risks to watch

- **E27 is the longest single experiment in the catalogue** (~30-45 min including CF create/delete). Budget the integration acceptance run accordingly.
- **E42 (concurrent-cold-thunder) needs careful concurrency.** Use `concurrent.futures.ThreadPoolExecutor` — not async. The harness is sync.
- **Lambda invocations must be properly counted.** CloudTrail is the only reliable way to count distinct invocations per second for E42. Query `LookupEvents` with `EventName=Invoke`.
- **E27's "waterfall" rendering is non-trivial.** It must show transitions across DNS / CF / Lambda / EC2 / DNS-swap on one timeline. Cap render at 80 columns, label each transition.
- **State-leakage between E40 runs.** If the wildcard you create in run N is still present when run N+1 starts, you measure the *previous* run's wildcard, not a clean baseline. E40's setup must verify a clean baseline before mutating.

---

## Acceptance

```bash
sg aws lab list                                       # 4 transition experiments now visible (~24 total)

# DNS-only composite
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E40 --ttl 60         # DNS-swap window
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E41                  # stop-race window

# Full system composites (require B+C merged)
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E42 --concurrency 10 --tier-2-confirm
SG_AWS__LAB__ALLOW_MUTATIONS=1 sg aws lab run E27 --tier-2-confirm

# verify
sg aws lab sweep --pending                            # finish CF deletes
sg aws lab sweep                                      # → "no leaked resources"
```

Plus:

```bash
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/lab/experiments/transition/ -v

# The final integration acceptance — gated, ~1h
SG_AWS__LAB__ALLOW_MUTATIONS=1 SG_AWS__LAB__DESTROY_TEST=1 \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/lab/test_safety_e27.py \
  --timeout=4000
```

---

## What "done" looks like for this slice

- E27's waterfall output prints a readable cold-path timeline (~25 lines) with all 5 transition labels (D, C, L, E, T).
- E40 prints a per-resolver flip-time table.
- E42 prints `concurrency=10, lambda_init_count=1, ec2_start_call_count=1, r53_change_count=1` (the v2 brief's correctness claim).
- The v2 brief's Q5 ("Lambda exits the data path within one TTL") has a measured answer.

---

## Commit + PR

Branch: `claude/aws-primitives-support-NVyEh-transition`. Commit prefix: `feat(v0.2.28): lab agent-D — composite transition experiments`.

Open PR against `claude/aws-primitives-support-NVyEh`. This is the last *experimental* PR — Agent E (viewer) is the only one that can land after you.
