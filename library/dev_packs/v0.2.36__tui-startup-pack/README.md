---
title: "TUI Startup Pack — briefing material for any new AWS-service TUI"
file: README.md
author: Architect (Claude)
date: 2026-05-20 (UTC hour 23)
repo: SGraph-AI__Service__Playwright @ claude/review-cf-logging-docs-QYfEq (v0.2.36 line)
status: GUIDE / PACK — reusable. Hand this to any agent starting a new TUI.
reference_instance:
  - team/humans/dinis_cruz/claude-code-web/05/20/23/v0.2.36__arch-brief__tui-cf-logs-and-architecture-visualisation.md
  - team/humans/dinis_cruz/claude-code-web/05/20/23/v0.2.36__arch-brief__tui-cf-first-screens-realtime-data.md
---

# TUI Startup Pack

A reusable pack for briefing **any new agent building a TUI over an AWS service** in the SG/Send ecosystem (CloudWatch, EC2, billing, Fargate, S3, CloudFront, …). It exists so each new TUI starts from a shared playbook instead of re-deriving the principles from a service-specific example.

> **The stance, up front: we are still learning the art of the possible.** This pack is for *exploration*, not production. Build screens to learn what shapes work; expect to keep some and discard others; document the negative results as carefully as the wins. Bounded effort per screen (a day or two), breadth over polish.

---

## What's in the pack

| File | What it is | When you read it |
|------|-----------|------------------|
| [`01__tui-playbook.md`](01__tui-playbook.md) | The service-agnostic charter — principles, module shape, framework, the data-source seam, deployment-chain rules, the simulate idea, the honesty rule, exploration definition-of-done | **First.** This is the doc you hand a new agent. |
| [`02__per-service-brief-template.md`](02__per-service-brief-template.md) | A fill-in skeleton — copy it, replace `{SERVICE}`, and you have a consistent brief for the new TUI | **Second.** Produce one per service before any code. |
| [`03__screen-idiom-catalogue.md`](03__screen-idiom-catalogue.md) | The recurring visual idioms (live tail, flow map, topology, inspector, dashboard, comparison, simulator) abstracted from real screens | **Alongside #2** — pick idioms off the shelf when choosing screens. |

**Reference instance #1 — CloudFront logs** (the two briefs in `reference_instance` above): a worked example of the playbook applied. Read them to see the pattern in the concrete; do **not** copy their CloudFront specifics into a new service brief.

---

## How to start a new TUI (the 4-step recipe)

1. **Read `01__tui-playbook.md`.** Internalise the stance and the architectural pattern.
2. **Copy `02__per-service-brief-template.md`** to `team/humans/dinis_cruz/claude-code-web/MM/DD/HH/` (or `team/comms/`), rename for your service, and fill it in — being ruthlessly honest in §1 about what real data exists *today* vs what is PROPOSED.
3. **Choose 3–6 screens** using `03__screen-idiom-catalogue.md`. Favour the screens that run on **real data you have right now** — those teach the most.
4. **Prototype, use for ~a week, then hold the "promotion" conversation** (playbook §9): which screens earn a place in a canonical TUI, which get dropped.

---

## Non-negotiables that carry into every TUI

- **Thin over primitives.** The TUI renders existing CLI/service primitives; it never owns parallel state. (CLAUDE.md: routes/views have no logic.)
- **Real data or labelled synthetic.** Never let a mockup imply PROPOSED machinery is live. Mark unknowns in the UI.
- **Type_Safe everywhere if you add primitives.** Any new schema/enum follows the project rules (no Pydantic, no Literals, one class per file).
- **Separate module.** A TUI never bloats the service package it visualises.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
