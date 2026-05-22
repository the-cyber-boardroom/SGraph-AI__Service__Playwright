---
title: "Bedrock Chat TUI — consuming & exposing the TUI API (chat-specific)"
file: 05__tui-api-tools-and-documents-plan.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 14 — slimmed from the hour-12 draft once the generic contract was extracted)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — chat-specific. The generic contract is now the ratified standard (see grounds_on).
parent: README.md
grounds_on:
  - "../../14/v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md  ← the ratified contract this doc consumes (decisions §10)"
  - sgraph_ai_service_playwright__cli/aws/bedrock/tui/   # the built chat (engine, inspector, cost model)
---

# Bedrock Chat TUI — consuming & exposing the TUI API

> **Scope changed (2026-05-21).** The generic TUI API — the contract schemas, capability
> tiers, **SG/Role** tokens, sequencing, the execution center, the loadout/workflow model,
> the orientation + change-control surfaces, and the VFS conventions — now live in the
> **ratified standard**:
> [`v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md`](../../14/v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md)
> (data-model decisions ratified §10). **This doc covers only what is specific to the
> Bedrock chat**: how it *consumes* the contract (the tool-use loop), how it *exposes its
> own* provider surface (standard decision #8), the VFS + documents as the chat sees them,
> and the chat slice plan. Where this used to define the contract (old §1–§9), it now points
> at the standard.

---

## 1. The chat as a TUI API consumer

The chat is given a **loadout** (a time-bounded set of SG/Role grants assembled from a
curated **workflow** — standard §4.6). It never picks its own tools (#10). From the loadout
it compiles a Bedrock `toolConfig` and runs a tool-use loop; **every** call goes through the
shared **execution center** (standard §4.7: AUTO / CONFIRM / DRY_RUN, SG/Role pre-flight,
audit).

```
build toolConfig from loadout.tool_config()   # only granted, in-tier, currently-AVAILABLE actions
  → converse(messages, toolConfig, system)     # sequencing (standard §4.2) means out-of-sequence
model emits stopReason='tool_use' (1+ blocks)  #   actions are never even offered to the model
  → for each: execution_center.execute(name, input)   # mode / SG/Role / dry-run policy applies
  → append toolResult content blocks
  → converse again
repeat until stopReason='end_turn'
```

- **toolConfig builder** (the one Bedrock-specific compile step): `Loadout.tool_config()` →
  Bedrock `toolConfig.tools[*].toolSpec` with the action's real JSON Schema as `inputSchema`.
  Only **granted ∧ in-tier ∧ currently-available** actions are emitted, and only their
  SKILL-api prose is injected — an unselected/over-tier/out-of-sequence capability is
  invisible to the model, not merely refused.
- **Cost — the per-turn sum across all sub-calls.** One user turn may be N Converse calls +
  M tool calls. The per-turn record sums **all** of them (critical given the cost focus);
  the cost meter gains a `calls: N model · M tools` line. This extends the built per-turn
  cost record, it does not replace it.

The loadout is presented in a modal (or a `--tools edge:read-only,s3:read-only` flag); the
shape is the standard's `Schema__Tui_Api__Loadout`:

```
┌─ tools for this chat (workflow: diagnose-edge-issue) ─────────────────────────┐
│  api            tier offered                granted        SG/Role             │
│ ▸ sg edge.slugs READ_ONLY · WRITE           [READ_ONLY ▾]  sg-edge.slugs:read  │
│   sg aws s3     READ_ONLY · CRUD            [READ_ONLY ▾]  sg-aws.s3:read      │
│   sg aws ec2    READ_ONLY · DESTRUCTIVE     [ off       ▾]  (would need :*)     │
│  granting WRITE+ shows the SG/Role + backing IAM that must be present · esc apply│
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The chat as a TUI API *provider* (standard decision #8 — v1, not later)

The chat is also a `Tui_Api__Provider` (standard §4.8), so it is driveable and inspectable
the same way the tools it consumes are. This is what makes "chat embedded in `sg edge tui`"
a real **TUI-of-TUIs** composition — the host drives the chat's provider surface.

| Surface | Backed by (already built) |
|---|---|
| `state()` | `Schema__Bedrock__Chat__Session` **is** the state surface — messages, turns, running cost aggregates, model, region, seeded context |
| actions | `send` · `clear` · `set_model` (Nova-only) · `export_brief` · `attach_document` |
| events | `turn_started` · `turn_completed` · `cost_updated` · `over_budget` |
| audit | each turn already records `request_json` + `response_text` — the audit/inspector trail |

```
sg aws bedrock chat tui api state            # the live session as structured data
sg aws bedrock chat tui api describe         # the chat's own manifest (actions/events/tiers)
sg aws bedrock chat tui api invoke send --params '{"text":"…"}'
sg aws bedrock chat tui api watch            # turn/cost events as NDJSON
```

Recommendation (open-Q §8): expose `state`/`watch` (READ_ONLY) by default; gate the
mutating actions (`send` etc.) behind a flag, since driving a chat headless spends money.

---

## 3. The VFS as the chat uses it

The VFS is a **core tool** (standard §6), disabled by default, granted per workflow. For a
chat session it is the *files-as-tool* surface: seed reference material once, and the model
pulls only what it needs via `vfs.read` — large reference sets cost ~zero tokens until
opened. Ephemeral by default (dies with the session, #6).

```
/tools/bedrock-chat/
  skills.md            # how to drive this chat well
  current-state.json   # the session snapshot (the state() surface, materialised)
  api/bedrock-chat.json
  <seeded reference material the operator dropped in>
```

Composes with documents (§4): **attach** when the model must read now; **VFS** when it
should read on demand.

---

## 4. Document support (chat-specific)

1. **Converse document attachments** — attach a file (pdf / txt / md / csv / docx / html /
   xls(x)) to a message; Nova reads it via Converse `document` content blocks
   (`{document:{format,name,source:{bytes}}}`). A picker (`^D`), an attached-docs chip row
   above the composer, and the **added input-token cost surfaced** per turn (and visible in
   the Inspector — the document is part of the exact request). Respect Bedrock limits
   (≤ ~4.5 MB, ≤ 5 docs/message); reject oversize with a clear hint.
2. **Persistent session context** — generalise the **built** single `--context FILE` (which
   today seeds one system block) to **N docs** as session context, labelled `[SEEDED]`. For
   *large* context, prefer the VFS read-on-demand path over inlining (avoids the
   context-pollution anti-pattern the standard §6 names).

RAG (chunk/retrieve) is explicitly **out** for v1 (needs an embedding store; changes the
cost/latency profile).

---

## 5. The Inspector extension (build on what exists)

The built Inspector (02 §8) already shows each turn's exact `request_json` / `response_text`
+ cost. Extend it for the tool loop:

- render `toolUse` / `toolResult` blocks inline per turn;
- show the execution center's audit entries (the TUI twin of the JS dev panel's `getLog()`);
- per-call cost attribution (which model round-trip / tool call cost what).
- Tool calls also render as collapsible **transcript** blocks (call · args · tier · result,
  with a ⚠ marker if the result was simulated/dry-run).

---

## 6. Chat slice plan (consumes the standard's foundations)

The contract, registry, execution center, SG/Role tokens, and VFS core tool are **standard
slices** (sequenced in the unified roadmap — see `04` §1). The chat-specific slices on top:

| Slice | Scope | Status |
|---|---|---|
| **P0 — chat provider surface** | the chat as `Tui_Api__Provider` (`state`/`actions`/`events`); `sg aws bedrock chat tui api …`. Decision #8 → **v1**. Pure + pilot. | proposed |
| **TL1 — engine tool-use loop** | Converse tool loop in the engine; toolResult; per-turn cost summing all sub-calls. | proposed |
| **TL2 — loadout + toolConfig** | loadout modal + `--tools` flag; `Loadout.tool_config()`; only granted ∧ available actions reach the model. | proposed |
| **TL3 — inspector extension** | toolUse/toolResult + audit + per-call cost in the Inspector; transcript tool blocks. | proposed |
| **D1 — documents** | Converse document attachments (picker + chip + cost) + N-doc persistent context. | proposed |

Build order: P0 first (cheap, avoids the redo trap, makes the chat testable headless), then
TL1→TL3 to make it agentic + visible, D1 in parallel.

---

## 7. Acceptance criteria (chat-specific)

| # | Criterion | Verification |
|---|---|---|
| 1 | The chat consumes a loadout; only granted ∧ in-tier ∧ available actions reach the model | pilot: over-tier / out-of-sequence action absent from `toolConfig` |
| 2 | Per-turn cost sums all model + tool round-trips; visible in meter + Inspector | pilot |
| 3 | The chat exposes its own provider surface; `… tui api state` returns the live session; driveable headless | pytest, no mocks (in-memory engine) |
| 4 | Documents attach to a turn / seed the session; added token cost is shown | pilot |
| 5 | Nothing mutates silently — WRITE+ tool calls gate via the execution center | pilot + unit |

---

## 8. Open questions (chat-specific)

| Question | Recommendation |
|---|---|
| Default loadout for a bare `chat tui` | **No tools** (pure chat) unless `--tools`/a workflow is given — least privilege by default. |
| Expose the chat's own provider surface by default? | `state`/`watch` (READ_ONLY) on; mutating actions (`send`…) behind a flag — driving a chat headless spends money. |
| Where does a chat session's VFS seed come from? | Defer to the standard's seeding open-Q (`--vfs-seed <dir>` recommended). |
| Attach vs VFS for a given doc | Attach when the model must read it **this turn**; VFS when it should read **on demand**. Surface both costs. |

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
