---
title: "Reality — sg aws lab"
domain: cli
subdomain: aws-lab
as_of: v0.3.0-foundation
last_updated: 2026-05-18
maintainer: Librarian
---

# `sg aws lab` — Reality

**Status: ✅ FOUNDATION LANDED** (`claude/aws-primitives-support-NVyEh`).
Experiment slices A–E are PROPOSED — not yet shipped.

---

## EXISTS — Foundation (v0.3.0)

### CLI surface (`sg aws lab`)

| Command | Status | Notes |
|---------|--------|-------|
| `sg aws lab list` | ✅ | Returns "no experiments registered" at foundation stage |
| `sg aws lab show <name>` | ✅ | Error if name not registered |
| `sg aws lab run <name>` | ✅ stub | Requires `SG_AWS__LAB__ALLOW_MUTATIONS=1`; errors if experiment not in registry |
| `sg aws lab sweep` | ✅ | Dry-run tag-driven leak scan |
| `sg aws lab sweep --apply` | ✅ | Actual deletion; requires `SG_AWS__LAB__ALLOW_MUTATIONS=1` |
| `sg aws lab account show` | ✅ | STS caller identity + region |
| `sg aws lab account set-expected` | ✅ | Sets `SG_AWS__LAB__EXPECTED_ACCOUNT_ID` guard |
| `sg aws lab runs list` | ✅ | Reads ledger; "no runs found" when empty |
| `sg aws lab runs show <run-id>` | stub | Returns "not implemented in foundation" |
| `sg aws lab runs diff <a> <b>` | stub | Returns "not implemented in foundation" |
| `sg aws lab ledger show` | ✅ | Dumps raw JSONL ledger as table or JSON |
| `sg aws lab ledger replay` | stub | Returns "not implemented in foundation" |
| `sg aws lab serve` | stub | Returns "not implemented in foundation" |

### Service layer (`sgraph_ai_service_playwright__cli/aws/lab/service/`)

| Class | Impl | Description |
|-------|------|-------------|
| `Lab__Runner` | ✅ full | Orchestrates experiment: setup → execute → teardown. `create_and_register()` writes ledger BEFORE factory call. |
| `Lab__Ledger` | ✅ full | Append-only JSONL at `~/.sg-lab/ledger.jsonl`; fcntl exclusive lock; partial-write recovery. |
| `Lab__Sweeper` | ✅ full | Tag-driven expired-resource scanner; routes to dispatcher for deletion. |
| `Lab__Tagger` | ✅ full | Extends `Aws__Tagger`; adds 5 `sg:lab:*` tags. Total 10 tags per resource. |
| `Lab__Safety__Account_Guard` | ✅ full | STS account-ID guard; `SG_AWS__LAB__EXPECTED_ACCOUNT_ID` env-var. |
| `Lab__Timing` | ✅ full | Monotonic wall-clock timer + sample builder. |
| `Lab__Phase__Not_Ready__Error` | ✅ | Exception class; raised by all non-R53 teardown stubs. |
| `Lab__Source__Adapter` | ✅ skeleton | Implements `Source__Contract`; empty streams. `register_all()` is LAZY. |
| `Lab__Experiment` (abstract base) | ✅ | `setup(runner)`, `execute() → Schema__Lab__Run__Result`, `metadata()`. |
| `experiments/registry.py` | ✅ | Empty at foundation; `register_experiment`, `get_experiment`, `list_experiments`. |

### Teardown layer (`service/teardown/`)

| Class | Impl | Description |
|-------|------|-------------|
| `Lab__Teardown__Dispatcher` | ✅ full | Maps `Enum__Lab__Resource_Type` → handler; `teardown_all()` sorts by `teardown_order`. |
| `Lab__Teardown__R53` | ✅ full | Re-reads record before delete (idempotent); uses `Route53__AWS__Client`. |
| `Lab__Teardown__CF` | stub | Raises `Lab__Phase__Not_Ready__Error`. |
| `Lab__Teardown__Lambda` | stub | Raises `Lab__Phase__Not_Ready__Error`. |
| `Lab__Teardown__ACM` | stub | Raises `Lab__Phase__Not_Ready__Error`. |
| `Lab__Teardown__EC2` | stub | Raises `Lab__Phase__Not_Ready__Error`. |
| `Lab__Teardown__SSM` | stub | Raises `Lab__Phase__Not_Ready__Error`. |
| `Lab__Teardown__IAM` | stub | Raises `Lab__Phase__Not_Ready__Error`. |

### Renderers (`service/renderers/`)

| Class | Impl |
|-------|------|
| `Render__Table` | ✅ full (Rich) |
| `Render__JSON` | ✅ full |
| `Render__Timeline__ASCII` | stub (Agent A) |
| `Render__Histogram__ASCII` | stub (Agent B) |

### Schemas / Enums / Primitives / Collections

All in `aws/lab/schemas/`, `aws/lab/enums/`, `aws/lab/primitives/`, `aws/lab/collections/`.

---

## PROPOSED — does not exist yet

### Agent A — DNS experiments (Phase P0 + P1)

**Depends on:** Foundation PR (this page). Targets: `propagation-timeline`, `zone-inventory`, resolver set measurements.

- `service/experiments/dns/` — concrete `Lab__Experiment__*` classes
- `service/renderers/Render__Timeline__ASCII.render_event_list()` — Agent A fills
- `Lab__Source__Adapter` streams: `lab-dns-*` streams for `sg aws observe`

### Agent B — Lambda experiments (Phase P2)

**Depends on:** v2 vault-publish phase 2b (Lambda primitive expansion).

- `service/experiments/lambda_/`
- `Lab__Teardown__Lambda.py` — full implementation
- `Render__Histogram__ASCII.render_durations_ms()` — Agent B fills

### Agent C — CloudFront experiments (Phase P3)

**Depends on:** v2 vault-publish phase 2a (CF primitive expansion).

- `service/experiments/cf/`
- `Lab__Teardown__CF.py` — full implementation
- `Lab__Teardown__ACM.py` — full implementation

### Agent D — Transition experiments (Phase P4)

**Depends on:** Agents A + B + C.

- `service/experiments/transition/`
- `Render__Timeline__ASCII.render_waterfall()` — Agent D fills
- `sg aws lab runs diff` — full implementation

### Agent E — Viewer + diff + HTML (Phase P5)

**Depends on:** Foundation.

- `sg aws lab serve` — Lab HTTP viewer
- `sg aws lab ledger replay` — teardown replay
- HTML report export
