---
title: "Bedrock Chat TUI — implementation plan"
file: 04__implementation-plan.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 10)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — exploration MVP. For human ratification before Dev picks up.
parent: README.md
---

# Bedrock Chat TUI — implementation plan

Slice sequence, testing, deployment-chain, acceptance, risks, and open questions. Mirrors
the `sg edge tui` plan: **pure data layer first (no Textual, runs on 3.11), reviewed on
its own; then the view in bounded slices.**

---

## 1. Unified roadmap (chat + TUI API)

The single roadmap for the whole effort. **Phase A (the chat)** is largely built on this
branch. **Phase B (TUI API foundations)** is the ratified standard's generic layer
([`../../14/v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md`](../../14/v0.2.36__tui-api-standard/01__tui-api-contract-and-conventions.md)).
**Phase C (chat ↔ TUI API)** wires them together (specified in `05`). Foundations (B)
precede the tool loop (C) so the chat engine isn't built twice — the briefs' "v1, not v2".

### Phase A — the chat (built)
| Slice | Scope | Textual? | Status |
|---|---|---|---|
| T1 — primitives + session core | two primitive extensions; schemas; `engine.send_turn`; in-memory source; card. Pure, 3.11. | no | ✅ built |
| S1 — chat screen (core loop) | transcript/`Chat__Bubble`/`Chat__Composer`, thread-worker streaming, anchor, per-bubble footer | yes | ✅ built |
| S2 — cost sidebar + caps | `Chat__Cost__Meter`, budget bar, pre-flight `check_cost_cap` → confirm modal, over-budget toast | yes | ✅ built |
| S3 — picker + theme/help/export | Nova `Model__Picker`, help modal, theme toggle, OSC-52 export | yes | ✅ built |
| S4 — brief + context seam | `Brief__Builder`/`Brief__Modal`; `--context FILE` seeding | yes | ✅ built |
| +Inspector (beyond original plan) | F2 request/response panel; `Turn.request_json`/`response_text` (02 §8) | yes | ✅ built |
| T-chain — deployment chain + docs | `… tui diagnose`; no-TTY one-shot; first-frame; guide; reality-doc | yes | 🟡 partial |

### Phase B — TUI API foundations (pure-first; the ratified standard)
| Slice | Scope | Textual? | Status |
|---|---|---|---|
| B1 — contract + registry | Type_Safe contract (standard §4), JSON-Schema-from-Type_Safe, `Tui_Api__Provider` + `Registry`, `sg <area> tui api list/describe/skills`; one read-only provider. Pure, 3.11. | no | ✅ **built** (`sg aws s3 tui api`; 14 tests) |
| B2 — SG/Role tokens + resolver | scope/grant/privilege; token resolver over `credentials/` + `aws/creds/`; whole-API `{api}:*` grant. Pure. | no | ✅ **built** (11 tests) |
| B3 — execution center | AUTO/CONFIRM/DRY_RUN, schema-validate, precondition/sequencing check, `ALLOW_MUTATIONS` gate, audit ring; `… tui api invoke`. Pure. | no | ✅ **built** (12 tests) |
| B4 — VFS core tool | `memory_fs`-backed provider; `/tools/<tool>/` conventions; `vfs.*` actions; ephemeral default. **3.12-gated tests.** | no | ✅ **built** (9 tests, 3.12) |
| B5 — explorer/tester | Swagger-style explorer screen + automated contract-test harness | yes | 🟡 **harness built** (contract gate); explorer screen pending |
| B6 — orientation + change-control | `Schema__Tui_Api__{Tool,Orientation,Change}` + `orientation()` provider method + `status`/`whatsnew`/`changelog` CLI. Change-capture recommended-not-enforced (§10 #5). Pure, 3.11. | no | proposed (ruled) |

### Phase C — chat ↔ TUI API (consumes B; see `05`)
| Slice | Scope | Textual? | Status |
|---|---|---|---|
| C-P0 — chat provider surface | the chat as `Tui_Api__Provider` (state/actions/events) — standard #8, **v1** | yes (+pure) | proposed |
| C-TL1 — engine tool-use loop | Converse tool loop; toolResult; per-turn cost summing all sub-calls | yes | proposed |
| C-TL2 — loadout + toolConfig | loadout modal + `--tools`; only granted ∧ available actions reach the model | yes | proposed |
| C-TL3 — inspector extension | toolUse/toolResult + audit + per-call cost; transcript tool blocks | yes | proposed |
| C-D1 — documents | Converse document attachments + N-doc persistent context | yes | proposed |
| (deferred) P — promote chat widgets | lift Tier-1 widgets to `_shared/tui/chat/`; wire `sg edge tui` chat mode | yes | deferred |

**Build order.** A is done. Do **B1→B3** (the framework-free core — independently useful as
`sg … tui api`), then **B4** (VFS, 3.12) and **C-P0** (cheap; makes the chat testable
headless and avoids the redo trap). **C-TL1→TL3** then make the chat agentic + visible;
**C-D1** runs in parallel; **B5** and the widget promotion land last.

---

## 2. Testing — no mocks, no patches (CLAUDE.md)

- **T1 (always runs, 3.11):**
  - `Bedrock__Stream__Adapter.extract_usage` / `collect_with_usage` — fed hand-built
    Bedrock stream-event dicts (delta events + a `metadata` event), assert text + exact
    `(in, out, latency)`.
  - `Bedrock__Chat__Engine.send_turn` — against `Bedrock__Chat__In_Memory` (a **real**
    scripted source returning canned deltas + a usage tuple, not a mock). Assert: the
    `Turn` cost equals `Bedrock__Cost__Calculator.estimate(...)`; the session aggregates
    sum correctly across turns; the messages list grows user/assistant alternately; the
    pre-flight cap raises when over.
  - `Bedrock__Chat__Card` / `Brief__Builder` — pure string assertions.
- **S1–S4 (gated `@skipUnless` textual importable):** Textual's async `App.run_test()`
  pilot, exactly as `sg edge tui` / `s3 tui` do — push keys, assert on widget/reactive
  state and on the real in-memory source the app was built with. Examples:
  - type into composer, `Enter`, `await pilot.pause()` (or `app.workers.wait_for_complete()`),
    assert a user bubble + an assistant bubble exist and the assistant text matches the
    scripted reply.
  - assert `app.session.total_cost_usd` and the meter's rendered `$` agree.
  - over-cap path: assert the confirm modal is pushed before any send.
  - `m` opens the picker and only Nova aliases appear; selecting `pro` changes
    `app.session.model_alias` but keeps the message history.
- **Gating note:** the view suite skips cleanly when Textual is absent (it isn't installed
  in every container); the T1 suite always runs. Pin Textual to a recent **8.x** in the
  TUI's install context (see §4).

---

## 3. Deployment-chain checklist (playbook §4)

- [ ] **Throttle to the link, not 60 Hz** — `MarkdownStream` coalescing does most of
      this for free; feed tokens as they arrive and let it batch.
- [ ] **First frame < 100 ms** — render the empty transcript + composer + sidebar
      immediately; the first turn is async.
- [ ] **Keyboard-primary** — every action has a binding (§ux 6); mouse optional.
- [ ] **Graceful resize** — `1fr` transcript + docked composer/sidebar re-layout cleanly.
- [ ] **`LANG`/`TERM` at container level** — coordinate with DevOps; the service image
      already needs this for `sg edge tui` (`ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
      TERM=xterm-256color`, `ncurses-term locales`).
- [ ] **`docker exec -it`** both flags.
- [ ] **`sg aws bedrock chat tui diagnose`** — `$TERM`, `$LANG`, `tput colors`, a unicode
      block test, a truecolor probe (copy the `sg edge tui diagnose` implementation).
- [ ] **No-TTY fallback** — piped/`$TERM=dumb` → one-shot single non-stream turn from
      stdin/arg, print response + cost line, exit. Keeps `chat tui` safe in CI/pipes.

---

## 4. Dependency note — pin Textual

`pyproject.toml:30` currently declares `textual = "*"`. Textual churns its API across
majors (the briefing confirms 3.x→8.x in under a year; `MarkdownStream` needs ≥5.0.0).
Per playbook §3.4, **pin the major** — e.g. `textual = ">=8,<9"` — so a future
`textual 9.x` can't silently break the streaming path. Textual stays operator tooling
(imported lazily; not loaded by the Lambda/Fargate runtime).

---

## 5. Acceptance criteria (exploration-grade)

| # | Criterion | Verification |
|---|---|---|
| 1 | `sg aws bedrock chat tui` runs an interactive Nova chat | manual + pilot |
| 2 | Streaming replies render smoothly (markdown, no flicker) | manual over SSM; pilot asserts bubble content |
| 3 | **Every turn shows exact tokens + USD; session aggregates them** | pilot: `Turn.cost_usd == calc.estimate(...)`; meter matches `session.total_cost_usd` |
| 4 | Cost survives streaming (not 0) via the `metadata` event | T1 unit test on `collect_with_usage` |
| 5 | Per-call cap enforced before send; over-cap → confirm modal | pilot |
| 6 | Nova-only model picker, priced | pilot: only 4 Nova aliases |
| 7 | Session cost is in-memory and discarded on close (no surprise persistence) | code review: no write on exit; capture only on explicit export/brief |
| 8 | Brief capture writes a usable dev brief to the agent-output folder | pilot + file assertion |
| 9 | Runs over SSM + `docker exec`, < 100 ms first frame, no-TTY fallback | tested in the chain |
| 10 | Chat widgets are contract-shaped for promotion to `_shared/tui/chat/` | code review against the Tier-1 contract |
| 11 | Per-slice notes captured (kept / discarded / why) | debrief per slice (good-failure convention) |

---

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Streaming loses token counts** (today's bug) → cost shows 0 | T1 extracts the `metadata` event; AC#4 gates it. This is the cost-critical fix. |
| **boto3 stream is blocking** → freezes the UI | thread worker + `call_from_thread`; `exclusive=True` so a new prompt cancels the old stream. |
| **Multi-turn cost creep** — history re-sent each turn grows input tokens | pre-flight `check_cost_cap` runs on the *full* history each send; budget bar makes spend visible; `^L` clears history to reset cost. |
| **Textual API churn** | pin major (§4); Tier-1 widgets thin; all logic/tests in the framework-free engine, so a Textual swap leaves the value intact (playbook §3.1). |
| **Premature shared-kit refactor** | build widgets in `bedrock/tui` first; promote to `_shared/tui/chat/` only at the sixth conversation (§1 deferred slice). |
| **Dishonest "synthetic" replies** | no synthetic mode; the only test double is the clearly-named in-memory source, never shown to an operator (playbook §7). |
| **Context seam leaks stale data** | context body is labelled + timestamped in the UI (`[SEEDED]`); it's a snapshot, not a live feed. |
| **Scope creep beyond Nova** | resolver filtered to `nova`; picker shows only Nova; Claude/Llama explicitly out of scope for v1. |

---

## 7. Open questions

| Question | Notes / recommendation |
|---|---|
| Single chat session, or tabs for several? | MVP: **one session** (simplest, bounded). `TabbedContent` for multiple is an easy later add. |
| Should `^L` clear *cost* too, or keep a session-lifetime running total? | Recommend: `^L` clears the conversation **and** resets cost (a fresh session); a separate "all-time this run" line is over-engineering for ephemeral data. |
| System prompt — fixed, or user-editable? | MVP: a small fixed system prompt + the optional `--context` block. Editable system prompt is a later toggle. |
| Brief synthesis — extra LLM turn (costs $) or template from transcript? | Recommend an explicit, **opt-in** Nova-lite synthesis turn (cheap, and its cost is captured like any turn); offer a no-LLM "raw transcript" brief as the fallback. |
| Where do exported briefs land — agent-output folder or `team/comms/`? | MVP: agent-output `…/MM/DD/HH/`; promote to `team/comms/` only when a human formalises one (CLAUDE.md scratch-vs-formal convention). |
| Does the cost sidebar earn its width, or should cost be a one-line status bar? | A genuine exploration question — build the sidebar, use it, decide at the promotion conversation. |

---

## 8. First concrete step

Build **T1** — the two primitive extensions + the session/engine/cost core, pure and on
3.11, with full unit coverage — and review it before any Textual code. It is independently
valuable: it also fixes the CLI's `--stream` "tokens = 0" reporting.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
