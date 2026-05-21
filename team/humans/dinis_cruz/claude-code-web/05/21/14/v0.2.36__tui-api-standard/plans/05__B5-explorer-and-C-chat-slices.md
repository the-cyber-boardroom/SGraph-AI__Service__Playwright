---
title: "B5 + C — explorer/tester and the chat consumption slices"
file: 05__B5-explorer-and-C-chat-slices.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 15)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — B5 (Textual+pytest) then the chat slices (consume B1–B4). Detail in pack-05.
parent: 00__plans-index.md
---

# B5 + C — explorer/tester and the chat slices

These depend on B1–B4. The chat-side design lives in
[`../../10/v0.2.36__bedrock-chat-tui-pack/05__tui-api-tools-and-documents-plan.md`](../../10/v0.2.36__bedrock-chat-tui-pack/05__tui-api-tools-and-documents-plan.md);
this plan sequences them and notes the build specifics.

---

## B5 — Swagger-style explorer + automated contract tester

**Goal.** One reusable surface to drive any provider through the **same** registry +
execution center the chat uses — manually (a screen) and automatically (a pytest harness).

### Files
```
tui/tool_api/
  screens/Tui_Api__Explorer.py        Textual: provider/action tree | JSON-Schema form | invoke -> result + audit
  screens/Tui_Api__Explorer__Render.py  pure markup helpers (testable on 3.11)
  cli/  (+ `tui api explore` command on the generic app from B1)
  tests/test_Tui_Api__Contract.py     the automated harness (3.11, no Textual)
```

### The automated contract tester (the high-value half — 3.11, no mocks)
For **every** registered provider, assert:
- the manifest validates; every action carries real JSON Schema (`properties` + `required`);
- any action with tier ≥ WRITE declares a scope/privilege;
- `supports_dry_run` actions actually preview without committing (via B3);
- a sample input per action schema-validates (build the params Type_Safe class);
- SKILL files exist and name every action.
This runs in CI with in-memory providers — no AWS. It is the guardrail that keeps every future
provider honest.

### The explorer screen (manual QA)
Provider/action tree on the left; the selected action's JSON-Schema rendered as a form; tier +
scope + SKILL prose; dry-run/real toggle; invoke → result + the audit entry. Pure render helpers
tested on 3.11; the Textual shell pilot-tested gated.

**Effort:** ~2 days (harness ~0.5d high-value; screen ~1.5d). Build the **harness first**.

---

## C — the chat consumes (and exposes) the TUI API

Sequence and per-slice notes (full design in pack-05):

| Slice | What | Depends on | Effort |
|---|---|---|---|
| **C-P0 — chat provider surface** | the chat as `Tui_Api__Provider`: `state()` from `Schema__Bedrock__Chat__Session`; actions `send`/`clear`/`set_model`/`export_brief`; events `turn_*`/`cost_*`; convert bedrock `tui` to a group + attach `api`. **v1, decision #8.** | B1 | ~1–1.5d |
| **C-TL1 — engine tool-use loop** | Converse `stopReason='tool_use'` loop in `Bedrock__Chat__Engine.send_turn`; toolResult blocks; per-turn cost sums all model + tool sub-calls. | B3 | ~2d |
| **C-TL2 — loadout + toolConfig** | `Loadout` from a workflow; `tool_config()` → Bedrock `toolConfig` (only granted ∧ available actions); loadout modal + `--tools`. | B1,B2,B3 | ~2d |
| **C-TL3 — inspector extension** | render toolUse/toolResult + B3 audit + per-call cost in the built Inspector; transcript tool blocks. | C-TL1 | ~1.5d |
| **C-D1 — documents** | Converse `document` content blocks (picker `^D` + chip + cost) + N-doc persistent context. | (parallel) | ~2d |

### C-P0 build notes (the cheap, first chat slice)
- `Bedrock__Chat__Session` already holds everything `state()` needs; each `Turn` already has
  `request_json`/`response_text` — the audit/inspector trail. So C-P0 is **wiring, not new state**.
- Reuse the `_engine_factory` seam (`Cli__Bedrock__Chat__Tui.py:17`) for headless provider tests
  (drive `send` via `tui api invoke` against the in-memory engine — no AWS).
- Recommendation (pack-05 §8): expose `state`/`watch` (READ_ONLY) by default; gate mutating
  actions behind a flag (driving a chat headless spends money).

### C-TL1/TL2 build notes (the Bedrock-specific work)
- osbot has `Schema__LLM_Request__Function_Call` + the Type_Safe→schema emitter, but **only an
  OpenAI platform** — the **Bedrock `toolConfig` mapping is new**: action → `{toolSpec:{name,
  description, inputSchema:{json: <emitter output>}}}`. Build it as `Bedrock__Tool_Config__Builder`
  in `aws/bedrock/tui/`.
- Cost: extend the existing per-turn record so a turn sums N Converse calls + M tool calls; the
  meter gains `calls: N model · M tools`. This is the project's cost-first differentiator over
  MCP-style exposure — keep it first-class.

---

## Suggested overall order

```
B1 ─▶ B2 ─▶ B3 ─▶ B4        (pure foundations; B1 ships as `sg aws s3 tui api`)
              └─▶ B5-harness (contract tester — guards every new provider)
B1,B3 ─▶ C-P0               (chat becomes driveable headless — cheap, avoids redo)
B3 ─▶ C-TL1 ─▶ C-TL3
B1,B2,B3 ─▶ C-TL2
C-D1 in parallel ; B5-screen + widget promotion last
```

Total foundations (B1–B4 + B5-harness): ~5–6 days. Chat slices (C): ~8–9 days. Each lands
independently with tests; nothing big-bangs.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
