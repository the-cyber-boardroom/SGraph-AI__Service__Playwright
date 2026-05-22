---
title: "Bedrock Chat TUI — architecture / UX / implementation pack"
file: README.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 10)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PACK — exploration brief, not production. Hand to Dev for the first slices.
parent: library/dev_packs/v0.2.36__tui-startup-pack/01__tui-playbook.md
grounds_on:
  - sgraph_ai_service_playwright__cli/aws/bedrock/        (the existing chat primitives)
  - sg_compute_specs/sg_edge/tui/                          (the flagship TUI pattern)
  - team/comms/plans/v0.2.38__sg-edge-tui/README.md        (the established module shape)
reference_textual_version: "Textual 8.2.7 (2026-05-19); MarkdownStream landed v5.0.0"
---

# Bedrock Chat TUI — pack

> **Exploration, not production** (TUI playbook §1). Each screen is a learning artefact.
> We are still learning the art of the possible for a *conversational* terminal UI —
> this is the project's first input-driven TUI, so expect to keep some shapes and
> discard others, and capture the negative results.

A Textual TUI for **`sg aws bedrock chat`** — a terminal chat experience over Amazon
**Nova** models, with **per-turn and per-session cost/token tracking** as a
first-class, always-visible concern. Built **reusable-component-first**: the
conversational widgets are designed to be lifted into *other* TUIs — most
immediately, a **"chat mode" for `sg edge tui`** so an operator can talk to the live
edge snapshot, diagnose gaps, and emit a dev brief for the coding agents.

---

## Why this, why now

The user is building rich, read-only TUIs (`sg edge tui` has five polished screens).
What's missing across all of them is the ability to **talk** to the data — to
diagnose, capture ideas, and turn them into action plans / dev briefs (the thing AWS
is reaching for with Q). A chat surface is that missing verb. `sg aws bedrock chat`
already has the LLM plumbing (Nova models, a cost calculator, streaming) — it just has
no interactive face. This pack puts a conversational face on it **and** factors the
chat UI into reusable parts so every future TUI can embed it.

Two hard constraints from the brief, designed in from the start:

1. **Nova only, to begin with.** The model picker is filtered to the four Nova
   aliases (`micro` / `lite` / `pro` / `premier`). Everything else (Claude, Llama) is
   present in the primitives but **out of scope** for this TUI's first cut.
2. **Cost is VERY important.** Every turn shows its own token count and USD cost; the
   session aggregates them in an always-visible meter with a budget bar. Session cost
   data is **in-memory only — it is fine to lose it when the TUI closes** (per the
   brief). Durable capture is opt-in (export / brief), not the default.

---

## What already exists (so we build *thin over primitives*)

Confirmed by reading the code — not assumed:

| Capability | Where | Reuse verdict |
|---|---|---|
| Single-turn `converse` + `converse_stream` | `bedrock/service/Bedrock__Runtime__AWS__Client.py` | **Reuse**, extend for multi-turn (§ arch 3.1) |
| Per-1M-token Nova pricing + per-call cap | `bedrock/service/Bedrock__Cost__Calculator.py` | **Reuse as-is** — pure, Type_Safe, already prices all 4 Nova |
| Nova alias table (`micro/lite/pro/premier` → model IDs) | `bedrock/service/Bedrock__Model__Aliases.py` | **Reuse** — filter resolver to `nova` |
| Per-turn schema (`input_tokens/output_tokens/cost_usd`) | `bedrock/schemas/Schema__Bedrock__Chat__Response.py` | **Reuse fields**; add a session aggregate |
| Stream→NDJSON adapter (delta extraction) | `bedrock/service/Bedrock__Stream__Adapter.py` | **Reuse**, extend to read the trailing `metadata` usage event (§ arch 3.2) |
| Capture writer (`~/.sg/aws/bedrock/chat/...`) | `bedrock/service/Bedrock__Capture__Writer.py` | **Reuse** for opt-in transcript + brief export |
| The TUI module shape (cli/screens/service/source/schemas/enums/tests + config) | `sg_compute_specs/sg_edge/tui/` | **Mirror exactly** |
| Pilot test harness, no mocks, gated on `textual` importable | sg_edge / s3 / cf TUIs | **Mirror exactly** |

Two **small, additive** primitive extensions are needed — both consistent with the
playbook's "extend the primitive, don't grow parallel state in the TUI" (§2.1):
multi-turn `converse(messages=[...])`, and extracting the streaming `metadata` event so
streaming yields accurate tokens/cost. Details in `01__architecture.md` §3.

---

## Reading order

| # | File | What it is | Read it for |
|---|------|-----------|-------------|
| 1 | [`01__architecture.md`](01__architecture.md) | Module layout, new Type_Safe schemas, the two primitive extensions, the session/cost model, the streaming-worker pattern, sequence walk-through | The engineering shape |
| 2 | [`02__ux-mockups.md`](02__ux-mockups.md) | ASCII mockups of every screen/modal/state, the "best 2026 text-chat UX" rationale, keybindings, cost-color tokens | What it looks and feels like |
| 3 | [`03__reusable-component-kit.md`](03__reusable-component-kit.md) | The shared chat component kit, mirroring the JS "reusable-component-first" model, and how `sg edge tui` embeds a chat mode | The reuse story |
| 4 | [`04__implementation-plan.md`](04__implementation-plan.md) | Slice sequence, testing (pilot, no mocks), deployment-chain checklist, effort, risks, open questions | How to build it |
| 5 | [`05__tui-api-tools-and-documents-plan.md`](05__tui-api-tools-and-documents-plan.md) | **Chat-specific** TUI API plan: how the chat *consumes* tools (the tool-use loop, loadout, cost-summing), *exposes its own* provider surface, and handles the VFS + documents | Wiring the chat to the TUI API |

> **The generic TUI API contract is now a standalone, ratified standard** (extracted from the
> old doc 05): [`../../14/v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md`](../../14/v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md)
> — the contract schemas, capability tiers, **SG/Role** tokens, sequencing, execution center,
> loadout/workflow model, orientation + change-control surfaces, and VFS conventions, with the
> 10 data-model decisions ratified. Read it before 05.

The per-service brief template (`tui-startup-pack/02`) is honoured across these:
data/primitives/seam → `01` §1–3; screens → `02`; honesty + deployment + acceptance →
`04`.

---

## The one-paragraph architecture

A thin Textual **view** (transcript of `Markdown` bubbles + a docked `TextArea`
composer + a docked cost sidebar) drives a pure **`Bedrock__Chat__Engine`** that holds
an in-memory **`Schema__Bedrock__Chat__Session`** (messages + per-turn cost records +
running aggregates). The engine calls a swappable **source** (live AWS via the existing
runtime client + stream adapter, or an in-memory fake for tests), streams deltas back
into the bubble via a Textual worker, reads the trailing `metadata` event for exact
tokens, prices the turn with the existing **`Bedrock__Cost__Calculator`**, and updates
the session aggregates that the sidebar renders. No business logic in the widgets; all
logic + cost + tests live in the Type_Safe layer, exactly as `sg edge tui` does.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
