---
title: "v0.2.29 — sg aws observe — unified observability v1 (Slice H)"
file: README.md
author: Architect (Claude)
date: 2026-05-17
status: PROPOSED — independent sibling pack of v0.2.29__sg-aws-primitives-expansion
size: M — ~1600 prod lines, ~700 test lines, ~3 calendar days
parent_umbrella: library/dev_packs/v0.2.29__sg-aws-primitives-expansion/
source_briefs:
  - team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__arch-brief__unified-observability-session.md
  - team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__addendum__s3-and-observability-additional-context.md
feature_branch: claude/aws-primitives-support-uNnZY-observability
---

# `sg aws observe` — Slice H

The unified-observability v1 REPL: a single interactive session that knows how to talk to S3, CloudWatch Logs, and CloudTrail uniformly via the Foundation-shipped `Source__Contract`. Plus one cross-source feature (`agent-trace`) and one-shot equivalents for scripting.

> **PROPOSED — does not exist yet.** Cross-check `team/roles/librarian/reality/` before describing anything here as built.

---

## Where this fits

This is **one of eight sibling slices** of the v0.2.29 milestone. The umbrella pack at [`v0.2.29__sg-aws-primitives-expansion/`](../v0.2.29__sg-aws-primitives-expansion/README.md) owns the locked decisions, the [Foundation brief](../v0.2.29__sg-aws-primitives-expansion/02__common-foundation.md), and the [orchestration plan](../v0.2.29__sg-aws-primitives-expansion/03__sonnet-orchestration-plan.md). **Read the umbrella first.**

**Dependencies:** This slice consumes `S3__AWS__Client` (Slice A) and `CloudTrail__AWS__Client` (Slice F). Both are mediated through the Foundation-shipped `Source__Contract` interface, so this slice runs in parallel with A and F — the final ~30 min before PR is a rebase to swap from the interface stubs to the real adapters.

---

## Source briefs

Two:

- [`v0.27.43__arch-brief__unified-observability-session.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__arch-brief__unified-observability-session.md) — the core architecture
- [`v0.27.43__addendum__s3-and-observability-additional-context.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__addendum__s3-and-observability-additional-context.md) — three layers (infra observability / product analytics / customer-facing reporting); v1 ships layer 1 only

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/observability/` (Foundation ships the skeleton; you fill in the bodies)

### Entry point

```
sg aws observe                   # enters interactive REPL
sg aws observe --command "..."   # one-shot command (no REPL)
sg aws observe replay <session>  # re-run a captured session
```

### REPL commands (per the source brief §"The Interactive Session Concept")

| Command | Purpose |
|---------|---------|
| `sources` | List connected sources + status + last-sync |
| `source connect <name>` | Connect (or reconnect) one source |
| `tail --source X --stream Y [--since DUR]` | Stream recent entries |
| `query "<dsl>" [--source X] [--since DUR] [--limit N]` | Run a query (per-source-capability) |
| `stats --source X --stream Y --by <field> [--since DUR]` | Aggregations |
| `schema --source X --stream Y` | Describe the source's fields |
| `agent-trace <vault-session-id>` | **The cross-source feature** — pulls the full trace of one session from every source |
| `dashboard fetch <name> [--time ts]` | (v2 stub — returns "not implemented in v1; see addendum") |
| `set --time-window <DUR>` | Adjust default time window |
| `set --default-source X` | Adjust default source |
| `history [--last N]` | Recent queries |
| `replay --capture <file>` | Capture this session for reproducibility |
| `help` | Inline help |
| `exit` / `quit` | Leave the session |

### One-shot equivalents

Every REPL command has a one-shot form for scripting:

```
sg aws observe tail --source cloudwatch --stream /aws/lambda/foo --since 1h
sg aws observe query "errors" --since 24h --json
sg aws observe stats --source cloudtrail --stream <trail> --by service --since 7d --json
sg aws observe agent-trace <vault-session-id> --json
```

### Sources for v1

| Source | Stream identifier | Backend |
|--------|-------------------|---------|
| `s3` | `s3://bucket/prefix/` | `S3__Source__Adapter` (Slice A) |
| `cloudwatch` | log group name | `CloudWatch__Source__Adapter` (wraps existing `aws/logs/`) |
| `cloudtrail` | trail name | `CloudTrail__Source__Adapter` (Slice F) |

Each adapter implements the `Source__Contract` from `aws/_shared/source_contract/`. Per the umbrella's locked decision #8, CloudFront-via-Firehose is a configured S3 prefix, not a separate source.

### The `agent-trace` cross-source query

Given a vault session ID, pulls the full trace by issuing parallel queries across the connected sources:

1. **From the vault** — the session's own commit history (which lives in the vault that captured the session)
2. **From S3** — the session's stdout/stderr captures (looks up `s3://sg-logs/<session-id>/...`)
3. **From CloudWatch** — Lambda or Fargate invocations correlated by `sg:session-id` tag
4. **From CloudTrail** — IAM/STS events with the session's caller identity in the same time window

Output: a unified timeline rendered as a Rich table (or NDJSON for `--json`).

---

## Production files (indicative)

```
aws/observability/
├── cli/
│   ├── Cli__Observe.py
│   └── verbs/
│       ├── Verb__Observe__Tail.py           # one-shot
│       ├── Verb__Observe__Query.py          # one-shot
│       ├── Verb__Observe__Stats.py          # one-shot
│       └── Verb__Observe__Agent_Trace.py    # one-shot
├── repl/
│   ├── Observability__REPL.py               # the interactive session loop
│   ├── REPL__Command__Parser.py
│   ├── REPL__State.py                       # session state: connected sources, time window, history
│   └── REPL__Capture.py                     # writes session to vault for replay
├── service/
│   ├── Source__Registry.py                  # the configured-sources registry
│   ├── Source__Orchestrator.py              # cross-source dispatch
│   ├── Agent__Trace__Composer.py            # builds the unified timeline
│   ├── CloudWatch__Source__Adapter.py       # wraps existing aws/logs/
│   ├── Query__Parser.py                     # the simple DSL
│   └── Renderers/
│       ├── Render__Timeline.py
│       ├── Render__Tail__Stream.py
│       └── Render__Stats__Table.py
├── schemas/                                 # Schema__REPL__State, Schema__Source__Config, Schema__Agent__Trace, etc.
├── enums/                                   # Enum__Source__Backend, Enum__Time__Window
├── primitives/                              # Safe_Str__Source__Name, Safe_Str__Stream__Name, Safe_Str__Vault__Session_Id
└── collections/                             # List__Schema__Source__Config, List__Schema__Agent__Trace__Row
```

---

## What you do NOT touch

- Any other surface folder under `aws/` (other than wrapping existing `aws/logs/`)
- `aws/_shared/source_contract/` (Foundation-owned; this slice IMPLEMENTS the contract, never modifies it)
- The product-analytics layer (addendum §4) — v2
- The customer-facing reporting layer (addendum §6) — v2
- AWS dashboard screenshots (addendum §2) — v2 (REPL stub returns "not implemented in v1")
- SG billing emission wiring (addendum §5) — depends on payments substrate; out of scope

---

## Acceptance

```bash
# enter REPL
sg aws observe
> sources                                                               # → s3, cloudwatch, cloudtrail listed
> source connect cloudtrail                                              # → "connected"
> tail --source cloudwatch --stream /aws/lambda/sg-test --since 30m
> query "errors" --since 24h --limit 100
> stats --source cloudtrail --stream <trail> --by event_source --since 7d
> agent-trace 2026-05-14T03:00:00Z__abc123
> history --last 5
> exit

# one-shot equivalents
sg aws observe tail --source cloudwatch --stream /aws/lambda/sg-test --since 30m
sg aws observe query "errors" --since 24h --json | jq length
sg aws observe agent-trace 2026-05-14T03:00:00Z__abc123 --json | jq '.timeline | length'

# replay
ls <vault-root>/observability/sessions/                                 # → capture from the previous interactive session
sg aws observe replay <vault-root>/observability/sessions/<session>     # re-runs the queries

# tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/observability/ -v
SG_AWS__OBSERVE__INTEGRATION=1 pytest tests/integration/sgraph_ai_service_playwright__cli/aws/observability/ -v
```

Acceptance criterion from the source brief: "the 'what was happening when X failed?' question is answerable in under 5 minutes." Validated against one real past incident as part of the integration acceptance — the operator runs the REPL against a known-bad time window and the report lives in the v0.2.29 debrief.

---

## Deliverables

1. All files under `aws/observability/` per the layout above
2. Unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/observability/` (in-memory adapters)
3. Integration tests under `tests/integration/sgraph_ai_service_playwright__cli/aws/observability/` (gated; uses real S3 + CloudWatch + CloudTrail backends)
4. New user-guide page `library/docs/cli/sg-aws/16__observe.md`
5. One row added to `library/docs/cli/sg-aws/README.md` "at-a-glance command map"
6. Reality-doc update: new `team/roles/librarian/reality/observability/index.md` (may need a new domain) or extend `aws-and-infrastructure/`

---

## Risks to watch

- **Slice A or F late.** Foundation ships interface stubs; build against those. If Slice A or F miss the integration window, ship Slice H with the missing adapters returning a clean `Source__Not__Available` error in the REPL; users can still use the other sources. The "three-source" acceptance criterion degrades to "two-source" and the user-guide notes it.
- **REPL UX.** Decision per source brief §"Open Questions" #1 — v1 ships a **REPL** (Python `cmd`-style or `prompt_toolkit`). TUI / notebook are v2. Lock to REPL; don't drift mid-implementation.
- **Query DSL.** Keep it simple. Free-text search with optional `field:value` filters. SQL-like is v2. Hard rule: no embedded code execution in the DSL.
- **Credential redaction in capture.** Captured sessions live in the vault. Redact `AWS_*` env vars, any `password`/`secret`/`token` substring before write. Tests must cover the redaction.
- **Large query results.** Default `--limit 100`; warn before fetching anything beyond 10K rows; require explicit `--no-limit` for unbounded queries.
- **CloudWatch Logs cost.** `FilterLogEvents` is billed per GB scanned. Pre-flight: estimate scan cost via the existing `aws/logs/` cost helper; require `--cost-override $X` if the predicted scan > `$SG_AWS__OBSERVE__MAX_SCAN_COST` (default $1.00).
- **Multi-region.** v1 operates in the current region only. `set --region <r>` switches; multi-region fan-out is v2.

---

## Commit + PR

Branch: `claude/aws-primitives-support-uNnZY-observability`

Commit message: `feat(v0.2.29): sg aws observe — unified observability REPL v1 (S3+CloudWatch+CloudTrail)`.

PR target: `claude/aws-primitives-support-uNnZY`. Tag the Opus coordinator. Do **not** merge yourself.

---

## Cancellation / descope

Independent (with the graceful degradation noted above for A/F late). Cancelling defers the unified observability work; the v0.2.30 product-analytics and customer-facing-reporting layers cannot proceed without it. No other v0.2.29 slice is affected.
