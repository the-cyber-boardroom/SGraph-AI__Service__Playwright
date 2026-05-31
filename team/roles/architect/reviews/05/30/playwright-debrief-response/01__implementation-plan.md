---
title: "Implementation plan — response to the v0.2.47 driving-session debrief + addendum"
file: 01__implementation-plan.md
author: Architect (Claude, Opus 4.8) — SGraph-AI__Service__Playwright
date: 2026-05-30
status: PLAN — for human ratification before code. Defines the 8 phases, what each ships, AND what is deliberately deferred or excluded.
inputs:
  - /root/.claude/uploads/.../sgplaywrightguide.md            # @Content's next-Claude guide (v0.2.47)
  - /root/.claude/uploads/.../sgplaywrightdebrief.md          # bugs + FR-1..FR-7
  - /root/.claude/uploads/.../sgplaywrightdebriefaddendum.md  # navigate-once / probe-many reframe
companion:
  - team/roles/architect/reviews/05/29/playwright-workbench-dev-pack/01__architecture-and-implementation-review.md  # original phasing (P0..P5) being superseded here
  - library/guides/v0.2.45__playwright-api-via-pw__claude-session-guide.md
---

# Implementation plan — v0.2.47 debrief response

> **Reframe vs the original dev-pack plan.** The Workbench team wrote a *brief*; @Content
> wrote a *report from real driving*. The latter reorders priorities meaningfully and
> introduces a new headline feature (`/pw/inspect` probe-batch). This plan is the new
> source of truth — it supersedes the phasing in `dev-pack/01` for everything below.

## 0. Headline shifts from the report

1. **BUG-2 is probably my regression from `415b331`** (typed `response_model` on
   `Routes__Sequence`). Highest priority — likely blocks every `get_content` caller.
2. **BUG-1** is upstream (`osbot-utils.Safe_Str__Url` excludes `:` from fragment). Real,
   but workaround-able. Fix locally; PR upstream later.
3. **Async engine (was P2) is deprioritised.** @Content's real-world driving confirms sync
   works fine once the verbs are real. Keep as a permanent peer (owner mandate) but ship
   it *after* the agent-debugging affordances.
4. **New headline feature: `/pw/inspect` probe-batch.** Addendum §2 — `navigate-once,
   probe-many` against one settled state. This is a *different unit of work* (action-
   pipeline → debug instrument). Architecturally fits cleanly on top of
   `Step__Executor__Base`.
5. **DOM-read is the universal unlock** — fixing `get_content` (BUG-2) + adding
   `get_dom_tree` ends the "I don't know what to wait on" cycle that forced the blind-wait
   anti-pattern.

## 1. The 8 phases — what's IN each

Naming is decoupled from the dev-pack's P0..P5 to avoid confusion.

### Φ1 — Bugfix block (P-bugfix)
**Goal:** stop the bleeding. Ship as one image build.

**In:**
- **BUG-2 fix.** Eliminate the polymorphic-list narrowing on
  `Schema__Sequence__Response.step_results`. Approach: lift the 6 subclass-specific result
  fields (`content`, `content_format`, `content_type`, `url`, `return_value`,
  `return_type`) onto `Schema__Step__Result__Base` as optional. The `Get_Content` /
  `Get_Url` / `Evaluate` subclasses become thin construction helpers (or get deleted —
  decide during implementation based on consumer count). A round-trip test asserts
  `content` survives the FastAPI `response_model` path; TestClient run in CI nails it
  end-to-end.
- **BUG-1 fix.** New `Safe_Str__Url__Permissive` primitive with RFC 3986 fragment class
  (adds `:` and the rest of `pchar` to the fragment regex). Swap the URL fields in:
  - `Schema__Step__Navigate.url`
  - `Schema__Step__Wait_For.url_pattern`
  - `Schema__Step__Result__Get_Url.url` (now on Base after BUG-2 lift)
  - `Schema__Screenshot__Request.url`, `Schema__Browser__Navigate__Request.url`
- **FR-5a — surface `evaluate`'s return value.** Today `execute_evaluate` discards it.
  Capture and put on the (now base-level) `return_value` / `return_type` fields. Half of
  FR-1c's `function` predicate is this.

**Out (deferred to Φ2+):**
- All new verbs (`wait`, richer `wait_for`, etc.).
- Probe-batch.
- Async engine.
- Upstream osbot PR (file an issue; ship local primitive now).

**Ship gate:** rebuild image; `GAP REPORT G-bug2` style probe from the v0.2.45 guide
returns populated `content`; URL with `:` fragment succeeds.

### Φ2 — Quick wins (P-quickwins)
**Goal:** kill the blind-wait anti-pattern in ~a day of work each.

**In:**
- **FR-4 plain `wait` verb.** New `Enum__Step__Action.WAIT`, `Schema__Step__Wait` with
  `ms: Safe_UInt__Milliseconds`, handler `time.sleep(ms/1000)` (sync engine; async engine
  uses `asyncio.sleep`).
- **FR-1a `wait_for: text`** — `page.get_by_text(...).wait_for(...)` with optional
  `selector` scope.
- **FR-1b `wait_for: selector_gone`** — `page.wait_for_selector(state="detached")`.
- **FR-7 artefact dimensions** — extract `width`/`height` from PNG bytes (PNG header
  parsing — stdlib `struct`; no Pillow dependency) and add to `Schema__Artefact__Ref`.
- **FR-7 viewport shorthand on `screenshot`** — optional `viewport: Schema__Viewport`
  on `Schema__Step__Screenshot` that sets the context viewport before snapping.

**Out:**
- `wait_for: function` (Φ3 — needs careful evaluator design alongside the read tools).
- `wait_for: network_idle_ms` (Φ3 — needs network-quiet tracking infra; pairs with
  console/network listeners).

**Ship gate:** `wait_for: {text}` resolves an SPA decrypt in @Content's vault case
without a blind wait.

### Φ3 — DOM reads + universal predicate (P-dom-reads)
**Goal:** end "I don't know what to wait on" forever. FR-2 in full.

**In:**
- **`get_text`** — visible text of page or `selector`. Lightweight.
- **`get_html`** — `outerHTML` of page or `selector`.
- **`get_dom_tree`** — *the high-value one.* Compact JSON tree:
  `{tag, id, class, role, accessible_name, rect, visible, child_count, children:[…]}`.
  Bounded by `max_depth` and optional `root_selector`. Sized cap (raise the inline cap if
  needed; document it).
- **FR-1c `wait_for: function`** — boolean predicate evaluated with a tight timeout. Same
  evaluator as Φ-eval below; this is one consumer.
- **FR-1d `wait_for: network_idle_ms`** — tunable network-quiet window. Requires Φ4's
  network listener; ship together.
- **FR-5b `accessibility_tree` artefact** (or a dedicated `get_a11y_tree` verb — decide on
  ergonomics during impl). `page.accessibility.snapshot()` → JSON.
- **FR-5d PDF artefact** — `page.pdf()`. Trivial; ship with §FR-2 since it's also a "read".

**Out:**
- Console + network logs *as step results* — those need listeners attached BEFORE navigate
  (Φ4); a per-step `get_console` would always be empty.
- Probe-batch (Φ5).

**Ship gate:** @Content's vault case is solvable end-to-end with `wait_for: text` →
`get_dom_tree` → real selector, no blind waits, no `get_content` regression.

### Φ4 — Console + network capture (P-load-listeners)
**Goal:** make load-time forensics available — addendum 4.3.

**In:**
- Attach `page.on('console')` and `page.on('requestfailed')` (and `page.on('request')`
  / `page.on('response')`) **before** `page.goto()`. Buffer into the sequence/probe
  context.
- New artefact types: `console_log` and `network_log`. Surfaced via either:
  - `capture_config.console_log.enabled = true` → terminal artefact (sequence end)
  - `wait_for: network_idle_ms = N` → consumes the request count (Φ3 dependency)
- **FR-5c console + network as artefacts** — this is the realisation.
- Per-step `get_console_tail(lines)` + `get_network_failures()` — for the probe-batch
  in Φ5 (architected here, used there).

**Out:**
- Full HAR / trace / video — Φ6 (context-level capture; bigger surface).

**Ship gate:** a navigate that loads a blank page returns one console line explaining why.

### Φ5 — Probe-batch + diagnostics-on-fail (P-probe-batch) — **the headline new feature**
**Goal:** addendum §2 + 4.1, 4.2, 4.4, 4.5, 4.6.

**In:**
- **`POST /pw/inspect`** — new route. Schema: `{navigate: NavigateSpec, settle: SettleSpec,
  probes: List[Probe]}`. Response: `{navigate: NavResult, settle: SettleResult,
  probes: Dict[str, ProbeResult]}` — keyed by `probe.id`, all probes always attempted
  regardless of any one's outcome.
- **`Probe__Executor`** in `sg_compute_specs/playwright/core/service/probe/` — sibling to
  `Step__Executor`. Inherits the read-only helpers; new dispatch table for probe types.
- **Snapshot-once, probe-many** (addendum 4.1): one navigate + settle, then fan out probes
  against the same `page` handle.
- **Probes shipped in Φ5:**
  - `selector_exists` (boolean)
  - `count(selector)` (int)
  - `resolve(candidates: List[selector])` → for each: `{exists, count, visible,
    text_sample, rect}` — addendum 4.6. Kills selector-guessing in one call.
  - `eval` (bounded; see Φ-eval below)
  - `dom_tree(root_selector?, max_depth?)` — reuse Φ3.
  - `text(selector?)`, `html(selector?)` — reuse Φ3.
  - `console_tail(lines)`, `network_failures()` — reuse Φ4.
  - `screenshot` — reuse Step executor.
  - `page_summary` macro (addendum 4.5) — server-assembled `{title, url, headings,
    landmarks, interactive_count, console_errors, failed_requests, shallow_dom}`.
- **`diagnostics_on_fail`** (addendum 4.4 — generalises FR-5c / G2). If `settle` times out
  OR any step in `sequence/execute` fails AND
  `sequence_config.diagnostics_on_fail = true` (new field), auto-attach: terminal
  screenshot + console tail + network failures + shallow DOM. **Surface as separate
  artefacts** (`step_index: null`, `purpose: "diagnostics"`).

**Out (deferred to Φ7 / spike):**
- Stateful session handle (`/pw/session/open` — addendum §6) — separate phase.
- Concurrent probe execution server-side (addendum 4.2) — interesting, but Playwright
  sync API doesn't trivially parallelise; defer to the async engine (Φ8) and then re-add
  here.
- Iframe / shadow-DOM piercing in `dom_tree` (FR-3) — Φ6.

**Ship gate:** an `/pw/inspect` request with the addendum §2 example body returns all
probes keyed correctly; `diagnostics_on_fail` triggers on a real failure with non-empty
artefacts.

### Φ6 — Shadow-DOM / iframe traversal + context capture (P-traversal)
**Goal:** FR-3 + the bigger half of FR-5c (HAR, trace, video).

**In:**
- `get_dom_tree` honours open shadow roots + same-origin iframes; boundaries marked
  (`"shadow_root":true` / `"iframe":true` on the node).
- Piercing selector convention — `>>>` (Playwright shadow-pierce) supported on all step
  verbs that take `selector`. Documented.
- `screenshot` accepts a `frame_selector` for sub-frame capture.
- Context-level capture (the *config-only* fields in `Schema__Capture__Config` get wired):
  - `video` (context.start_video + new_context options)
  - `har` (`record_har`)
  - `trace` (`tracing.start()` / `tracing.stop()`)
  - All written via `Artefact__Writer` (the only sink-touching class) — the vault sink
    finally needs implementing here, otherwise these are only useful inline.
- Vault/S3 sink seams (`write_bytes_to_vault` / `write_bytes_to_s3`) — wire at least one
  real implementation (probably S3 first since the vault is a different service).

**Out:**
- Cross-origin iframe piercing (browser security limit — not our bug).
- Trace ZIP viewer integration (client-side problem).

**Ship gate:** a single sequence captures HAR + video to S3 and returns refs; their
sizes/durations are sane.

### Φ7 — Session handle (opt-in stateful) (P-session-handle)
**Goal:** addendum §6 — amortise navigate+decrypt across multiple probe batches.

**In:**
- `POST /pw/session/open` → `{session_id, expires_in_ms}` (bounded by existing
  `max_session_lifetime_ms` capability).
- `POST /pw/session/{id}/probe` — accepts the same probe body as `/pw/inspect`, runs
  against the held page.
- `POST /pw/session/{id}/act` — accepts a `sequence/execute`-style body, runs steps,
  page state persists.
- `POST /pw/session/{id}/close` — explicit cleanup; auto-close on TTL.
- One session per token; storage in-process (no cross-replica sharing — single-instance
  for now).
- Auto-cleanup: TTL sweep thread (existing watchdog pattern).

**Out:**
- Cross-replica session sharing (would need shared state — explicitly out of scope).
- Session migration between containers (same — single ephemeral EC2).
- Sticky-session routing (not needed for single instance).

**Ship gate:** a vault-decrypt + 5 probe batches against the held page runs in well
under the wall-clock of 6 fresh requests.

### Φ8 — Async engine leaf (P-async — owner mandate, deprioritised)
**Goal:** ship the parallel async engine on top of `Step__Executor__Base` (already
extracted in commit `fc7cc70`).

**In:**
- `Step__Executor__Async(Step__Executor__Base)` — same dispatch table, `await page.*`.
- `Browser__Launcher__Async` — `async_playwright()` lifecycle.
- `Sequence__Runner__Async` — engine-neutral orchestration logic shared with sync; if a
  `Sequence__Runner__Base` extraction is needed during this phase, do it (mirror what was
  done for the executor).
- `POST /pw/sequence/execute-async` (and matching `/inspect-async` if cheap) — same
  request/response contract; `engine: "async"` reported. `requested_engine` request field.
- Concurrent probe execution server-side (addendum 4.2) — natural fit for async.

**Out:**
- Removing the sync engine. Owner mandate: keep both first-class.
- Streaming responses (SSE) — addendum mentions this; Φ9+ if ever.

**Ship gate:** the regression checklist from the original dev-pack (per-verb smoke,
artefact round-trip, isolation, halt, timeout, concurrency, CORS, spec accuracy, health)
all green against both engines.

## 2. What we are NOT implementing (explicit non-goals)

To remove ambiguity — these came up in the docs but are **out** for this 8-phase response,
either because they belong elsewhere or because they don't fit the service shape:

| Ask | Where it came from | Why it's out (or where it actually belongs) |
|---|---|---|
| Live screencast (Page.startScreencast relay) | Original brief §7.11, addendum (implicit) | Architecturally belongs with visible-browser specs (`vnc`/`firefox`), not this stateless headless service. Track as a separate spec spike — see dev-pack/01 §8. |
| CDP websocket relay for remote control | Original brief §7.12 | Same — separate spec, different lifecycle (token-scoped lease, browser teardown semantics). Owner explicitly OK with experimenting later; not in this 8-phase response. |
| Idempotent `sequence_id` dedupe | Original brief §7.8 — **WITHDRAWN by Workbench team** in their answers (Q12) | Withdrawn; do dedupe client-side. |
| SSE / chunked streaming of step results | Original brief §7.10 | Defer; the async engine (Φ8) is a prerequisite. Re-evaluate after Φ8. |
| Cross-replica session sharing | Implied by §7 (Φ7) | Out of scope — single ephemeral EC2 instance per stack. |
| Native retries (`retry: {count, delay_ms}` on steps) | Brief §7.6 | Defer past Φ8. Client-side retries are sufficient given per-step `error_type` is now structured. |
| Network/route control (block resource types, stub responses) | Brief §7.5 | Defer past Φ8. Real demand will pick this up. |
| Per-step timings breakdown (navigation vs script vs wait) | Brief §7.9 | Defer past Φ8. The single `duration_ms` per step is sufficient for now. |
| Native assertion verbs (`expect_selector_visible`, `expect_title_contains`, …) | Brief §7.2 / Q11 | **De-facto delivered by Φ5 probe-batch** (`selector_exists`, `eval`, etc.) — the probe model is a strictly more expressive form of assertions. Skip the per-step `expect_*` verbs unless real demand survives Φ5. |
| Removing the sync engine | — | Owner mandate is to **keep both**. |
| Upgrading the inline-bytes size cap unconditionally | Brief §4 / G in the v0.2.45 guide | Document the actual cap (Φ1 or Φ3). Raise only if a real workload demands. |
| Upstreaming the URL-primitive fix to `osbot-utils` | BUG-1 | File a separate upstream issue/PR. Local primitive (Φ1) unblocks us immediately. |

## 3. Headline shape changes to the API across the 8 phases

By end of Φ5 the API has two distinct primitives (deliberate split):

- **`POST /pw/sequence/execute`** — *act*. Linear pipeline; halts on error by default;
  artefacts are per-step outputs. This is what's there today.
- **`POST /pw/inspect`** — *understand*. One navigate+settle, then a batch of independent
  read-only probes against the settled state; results keyed by `probe.id`; never halts on
  individual probe failures; auto-attaches diagnostics on settle failure.

By end of Φ7, a third opt-in primitive:

- **`POST /pw/session/{open,probe,act,close}`** — *sustain*. Short-lived stateful handle
  so the navigate+decrypt cost amortises across multiple debug rounds. Bounded by token,
  TTL, single-instance.

By end of Φ8 each of the above has an `-async` peer; the `engine` field on every response
reports which engine ran.

## 4. Risk register

| Risk | Mitigation |
|---|---|
| The Φ1 BUG-2 fix (lift-fields-to-base) is ugly. | Acceptable — it's bulletproof and the response shape stays exactly what @Content's session already parses. If we ever want pure subclass typing, the `Step__Executor__Base` refactor pattern makes a discriminated-union retrofit cheap. |
| Φ4 console/network listeners must attach BEFORE navigate, but the current model launches the browser inside the runner per request. | Listener attachment moves into `Browser__Launcher.launch` (or a runner hook fired just after launch, before any step runs). Test: a navigate that errors leaves at least one console line in the buffer. |
| Φ5 probe-batch evaluator (`type: "eval"` / `wait_for: function`) widens the JS surface beyond today's strict allowlist. | Bounded eval mode: wall-clock timeout + size-capped JSON result; documented allow-list of helpers (`$count`, `$text`, `$attrs`, `$exists`, `$sections`) as the conservative first step; full eval gated by a config flag. Addendum 4.8 spells it out. |
| Φ6 trace/video on a stateless ephemeral instance fills disk. | Sweep on request completion (success + failure). Set per-request size caps. Already required by §7.3 statelessness — enforce here. |
| Φ7 session handle re-introduces server-side state — tension with statelessness. | Bounded: single-instance, single-token, TTL, opt-in. The original `/pw/sequence/execute` and `/pw/inspect` remain stateless — sessions are an explicit second mode. Document loudly. |
| Φ8 async engine duplicates orchestration logic. | The `Step__Executor__Base` extraction (already shipped) is the model. Mirror it for the runner when needed. |

## 5. Image-version bumps per phase

Per the new single-source convention (root `/version`, auto-bumped by `increment-tag`):
each phase publishes a new `diniscruz/sg-playwright:v0.2.N` tag; no overwrites. No manual
bumps unless a phase splits into multiple builds.

## 6. What I want from the owner before starting Φ1

1. **Confirm the re-ordering** — async (Φ8) genuinely after the agent-debugging
   affordances (Φ1-Φ7).
2. **Confirm Φ5 (`/pw/inspect`) is in-scope** as a new endpoint, not a `probes:` block on
   `sequence/execute`. The addendum is open on this; I picked a separate endpoint because
   it's cleaner (different unit of work → different route).
3. **Confirm probe-batch's `eval` mode** can be bounded-but-expressive (addendum 4.8) for
   *probe-batch only*, while keeping `sequence/execute`'s `evaluate` step strictly
   allowlisted. Two modes, different blast radius.
4. **Confirm the BUG-2 fix shape** (lift-fields-to-base) — ugly but bulletproof — vs the
   alternative (discriminated union, Pydantic-specific, may not flow through Type_Safe).

## 7. After ratification

I'll work Φ1 → Φ7 as separate commit slices (each ship-able), pausing for live validation
after Φ1 (the BUG-2 fix), Φ3 (DOM reads — the real "no more blind waits" gate), and Φ5
(the probe-batch — biggest UX shift). Φ8 (async) lands last.
