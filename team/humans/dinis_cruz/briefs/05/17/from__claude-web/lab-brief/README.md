---
title: "Architect Briefing — sg aws lab: a behaviour-characterisation harness for the DNS / CF / Lambda primitives"
file: README.md
author: Architect (Claude)
date: 2026-05-16 (UTC hour 15)
repo: SGraph-AI__Service__Playwright @ dev
status: BRIEF — no code yet, for human ratification before Dev picks up.
parent:
  - team/humans/dinis_cruz/claude-code-web/05/16/15/v0.2.23__brief__vault-publish-spec__v2/
related:
  - team/humans/dinis_cruz/claude-code-web/05/15/03/architect__vault-app__cf-route53__plan.md
  - team/humans/dinis_cruz/claude-code-web/05/15/08/architect__sg-aws-dns__plan.md
  - library/dev_packs/v0.2.11__vault-publish/  (SUPERSEDED by v2 brief)
---

# Architect Briefing — `sg aws lab`

A behaviour-characterisation harness for the primitives the v2 brief depends on: Route 53 propagation, CloudFront origin behaviour (including error-response failover), and Lambda invocation patterns. The deliverable is a set of small, composable, **safely-revertible** experiments that turn each of the v2 brief's "we assume this works" lines into a *measured* fact.

> **PROPOSED — does not exist yet.** No code in `sgraph_ai_service_playwright__cli/aws/lab/` today (verified — the directory does not exist; `sg aws cf` and `sg aws lambda` from the v2 brief are also still PROPOSED).
> This brief is the **measurement layer underneath the v2 brief.** It can land before, in parallel with, or after `sg aws cf` / `sg aws lambda`. Most of the value lands without those primitives existing yet — see [§7](07__phasing.md) for the dependency map.

---

## Read order

| # | File | What it covers |
|---|------|----------------|
| 00 | this README | Goals, why, the cleanup-or-die principle, the four pillars |
| 01 | [`01__intent-and-principles.md`](01__intent-and-principles.md) | What we are trying to learn; the seven principles that govern the harness |
| 02 | [`02__component-decomposition.md`](02__component-decomposition.md) | The v2 workflow broken into ~22 testable units. Tagged by AWS surface |
| 03 | [`03__experiment-catalogue.md`](03__experiment-catalogue.md) | The full list of named experiments (~30), each with input / output / what-it-proves |
| 04 | [`04__safety-and-cleanup.md`](04__safety-and-cleanup.md) | The Resource-Ledger / TTL-stamp / atexit / leak-sweeper design. How we guarantee zero leakage |
| 05 | [`05__module-layout.md`](05__module-layout.md) | Folder structure, class layout, schema list, CLI surface |
| 06 | [`06__ui-and-visualisation.md`](06__ui-and-visualisation.md) | The terminal-first dashboard; optional FastAPI viewer; what a "result" looks like |
| 07 | [`07__phasing.md`](07__phasing.md) | Five-phase rollout. Each phase ships a usable harness on its own |
| 08 | [`08__open-questions.md`](08__open-questions.md) | Decisions the human must rule on before Dev picks up |

---

## Two-paragraph TL;DR

The v2 vault-publish brief leans on three primitives — Route 53, CloudFront, Lambda — and on **emergent behaviour** between them: specific-record-beats-wildcard, TTL convergence, CloudFront origin-error pickup, cold-start latency, Lambda concurrency. None of this is in our test suite today. The current tests prove our *code* is right; they say nothing about whether the *AWS layer* will do what we expect. Before we commit to the v2 brief's phasing — particularly the "Lambda exits the data path within one TTL" claim, which is the whole architecture — we should *measure*, not assume.

This brief proposes `sg aws lab`: a Typer surface, mirroring `sg aws dns` exactly, that hosts ~30 named experiments. Each experiment provisions a tiny, throwaway AWS resource set, measures one specific behaviour (e.g. "how long after `upsert_record` does each of the 6 public resolvers see the new value?"), prints a typed result with timings, and tears the resources down **whether the experiment passes, fails, or is Ctrl-C'd**. Cleanup is enforced by three independent mechanisms ([§4](04__safety-and-cleanup.md)) so a single failure cannot leak resources. The output of each run is a Type_Safe schema (`Schema__Lab__Run__Result`) that the harness can render as a table, a timeline plot, or a CloudWatch-Logs-Insights-style JSON dump.

---

## Four pillars

### Pillar 1 — Decomposition

Break the v2 workflow into **the smallest units that compose into a behavioural claim**. Each unit gets one or more experiments. See [§2](02__component-decomposition.md). Examples:

- "Route 53 `upsert_record` → INSYNC time" (one unit)
- "INSYNC → authoritative-NS visibility on all 4 NS" (a different unit)
- "Authoritative visibility → caching-resolver visibility, per resolver" (a third unit)
- "Specific record present + wildcard alias present → which one does each resolver return?" (a *composite* unit — only meaningful as a measurement of the whole DNS layer)

### Pillar 2 — Safety

**No experiment may leak resources.** This is non-negotiable; the harness is useless otherwise. We achieve it with three independent layers:

- **Resource Ledger** — every `create_*` call is paired with a `register_for_cleanup(...)` call. The ledger persists to disk (`.sg-lab/ledger/<run-id>.jsonl`).
- **Atexit / signal handler** — the ledger replays in reverse on normal exit, exception, SIGINT, SIGTERM.
- **Leak sweeper** — `sg aws lab sweep` lists every resource tagged `sg:lab=1` older than a TTL and offers to delete them. Run at session start.

See [§4](04__safety-and-cleanup.md) for the full design.

### Pillar 3 — Visualisation

A measurement nobody can read is wasted. Every experiment ships:

- a **terminal table** (Rich) showing the key numbers at a glance,
- a **timeline ASCII plot** for time-series experiments,
- a **JSON dump** suitable for diffing across runs,
- optionally, an **HTML report** rendered by a small FastAPI viewer (`sg aws lab serve`).

See [§6](06__ui-and-visualisation.md).

### Pillar 4 — Reproducibility

Every experiment is deterministic in its scaffolding: same name pattern, same tags, same ledger format, same teardown order. Re-running an experiment back-to-back gives comparable timings. Runs are stored under `.sg-lab/runs/<utc-timestamp>__<experiment-name>/` and can be diffed.

---

## What this brief is NOT

- **Not a replacement for unit tests.** Unit tests with in-memory clients run on every push; this harness runs against real AWS and costs real money (very little, but non-zero). The two coexist.
- **Not a CI gate.** Experiments run on demand, by a human operator, under `SG_AWS__LAB__ALLOW_MUTATIONS=1`. CI never invokes the harness.
- **Not a load test.** We are characterising *correctness and timing of single events*, not stress-testing the primitives.
- **Not a substitute for the v2 brief landing.** This is a measurement scaffold; the v2 brief is the system we are measuring.
- **Not a permanent fixture.** Once a behaviour is well-understood, its experiment can be retired (or kept as a regression check, run weekly).

---

## Headline claim

> *"Before we write a line of `Waker__Handler`, we should know — to the millisecond — how long the cold path actually takes, where time is spent, and which of the v2 brief's assumptions are tight, loose, or wrong."*

If the harness lands first, the Dev work on v2 ships with measurement-backed confidence rather than architecture-on-paper confidence. That alone justifies the spend.
