---
title: "Architecture & Implementation Review — sg-playwright changes for the Playwright Workbench"
author: Architect (Claude, Opus 4.8)
date: 2026-05-29
repo: SGraph-AI__Service__Playwright @ claude/cool-bell-GLbss (v0.2.41 line)
status: REVIEW — code-grounded plan for human ratification. No service code changed yet.
reviews: 00__original-brief__from-workbench-team.md
owner_steering:
  - "Keep BOTH sync and async execution paths (by design, for now). Fix sync; add async; share as much code as possible."
  - "Take this opportunity to clean up and improve the code."
  - "This is critical infrastructure — focus on refactor and code quality."
---

# Architecture & Implementation Review

> **How this was produced:** every claim in the brief was checked against the actual code in
> `sg_compute_specs/playwright/core/` (routes, `Playwright__Service`, `Sequence__Runner`,
> `Step__Executor`, `Browser__Launcher`, `Artefact__Writer`, the schema tree). Where the brief's
> "root cause (our read)" differs from what the code does, the code wins and I say so. The brief is
> **accurate on intent and priorities**; it is **partly wrong on the current state of the code**,
> which is expected — it was written from the outside, by probing the HTTP surface.

---

## 1. Executive summary — what's actually true

| Brief's claim | Reality in the code | Verdict |
|---|---|---|
| §2 "screenshot crashes the whole sequence with *sync-Playwright-in-asyncio*" | An asyncio-loop **guard already exists**: `Playwright__Service._run_sequence_via` (lines 119–127) detects a running loop and dispatches the sync run into a fresh `ThreadPoolExecutor`. Routes are sync `def` (FastAPI runs them in a worker thread). | **Partly fixed already; partly misdiagnosed.** The deployed `:latest` the brief tested is almost certainly **older than committed HEAD** (version drift). |
| §2 "navigate works, screenshot fails" | The likely real trigger: **`wait_for` is an unimplemented stub** that `raise NotImplementedError` (see below), and the runner does **not** wrap step execution in try/except. The brief's failing repros all include `wait_for`. | **Misattributed.** The abort is probably the unimplemented verb, not the screenshot. |
| §3.1 "per-step isolation + halt_on_error missing" | **Already implemented** in `Sequence__Runner.execute` (per-step `status`, `halt_on_error`, deadline→`skipped`, guaranteed teardown via try/finally) — *for implemented verbs*. | **Mostly done.** Needs one hardening fix + docs. |
| §3.3 verb vocabulary (`navigate … dispatch_event`) | **9 of 16 verbs are unimplemented stubs**: `press, select, hover, scroll, wait_for, set_viewport, dispatch_event, video_start, video_stop` all `raise NotImplementedError`. Only `navigate, click, fill, screenshot, get_content, get_url, evaluate` work. | **Major gap the brief underestimates.** Their own examples §5.2/5.3/5.4 cannot run today. |
| §4 capture_config (video/har/trace/console/terminal screenshot) | The `Schema__Capture__Config` is rich (all those fields exist) but **only per-step `screenshot` + `get_content` inline are wired at runtime**. `screenshot_on_fail`, terminal capture, `page_content`, `video`, `pdf`, `har`, `trace`, `console_log`, `network_log` are **schema-only / not implemented**. | **Config exists; behaviour doesn't.** §4.1's hybrid model is the right target. |
| §3.2 "type the 200 response" | `Schema__Sequence__Response` **exists** (Type_Safe) but the route returns `.json()` (a dict), so FastAPI advertises it as untyped `string`. | **Valid, small fix** (wire `response_model`). |
| §3.4 CORS inconsistent | In the **`/pw` proxy architecture** CORS is the *vault's* job (fixed earlier this session). Direct cross-origin to sg-playwright is a separate, currently-minimal config. | **Real, but conflated.** Two access modes; see §7. |
| §7.3 statelessness | `Browser__Launcher.launch` already does a **fresh `sync_playwright().start()` + fresh browser per request**, torn down in try/finally. | **Largely already true.** Needs a temp-file audit. |

**Bottom line:** the single most valuable change is **not** "rewrite to async" — it is **(1) implement the missing verbs and (2) make the runner isolate *any* step exception**, which together fix the brief's real blocker (sequences abort). The async path is then added *in parallel, by owner mandate*, as a clean second engine sharing the same orchestration code.

---

## 2. The real blocking bug (§2) — corrected diagnosis

The brief's repro:

| Sequence | Result |
|---|---|
| `[navigate]` | 200 |
| `[navigate, wait_for, screenshot]` | 400 |

The brief concludes "screenshot triggers a sync-in-asyncio crash." But **both `navigate` and `screenshot` call the sync Playwright API on the same page in the same thread** — if an event loop were the problem, `navigate` would fail too. It doesn't. So the event-loop theory cannot be the whole story for the *current* code.

Two mechanisms actually explain the failures, and the fix differs for each:

### 2a. Version drift (the asyncio error specifically)
The exact message *"Playwright Sync API inside the asyncio loop"* is real and comes from Playwright when the sync API runs on a thread with a live event loop. Committed HEAD already guards against this (`_run_sequence_via` → `ThreadPoolExecutor`). If the brief still sees it, **the deployed `:latest` predates that guard.** → **Action P0:** rebuild `:latest` from HEAD and re-run the brief's exact repro before writing any async code. This may close §2 outright for the sync path.

### 2b. Unimplemented verbs abort the sequence (the actual "one step 400s everything")
`Step__Executor` (lines 195–203):

```python
def execute_press(self, …):  raise NotImplementedError(f'PRESS: {DEFERRED_MESSAGE}')
def execute_wait_for(self, …): raise NotImplementedError(f'WAIT_FOR: {DEFERRED_MESSAGE}')
# … select, hover, scroll, set_viewport, dispatch_event, video_start, video_stop
```

And `Sequence__Runner.execute` (line 125) calls `self.step_executor.execute(...)` **without a try/except** — it trusts each handler to return a result. Implemented verbs honour that (each has an internal `try:` → `failed_result`). The **stubs raise**, the exception propagates out of the loop, past the `finally` (browser teardown still runs — good), and out of `execute()` → HTTP 4xx/5xx with no `step_results`. Every brief example that includes `wait_for`/`press` hits this.

**This is the true cause of "a single step aborts the whole request"** — not async. Fixing it needs two things, both cheap:

1. **Implement the missing verbs.** They are thin sync Playwright calls (`page.wait_for_selector`, `page.keyboard.press`, `page.select_option`, `page.hover`, `page.mouse.wheel`/`locator.scroll_into_view`, `page.set_viewport_size`, `page.dispatch_event`). `video_*` need context-level recording (defer with HAR/trace to Phase 3). A QA tool is unusable without `wait_for` at minimum.
2. **Harden the runner** — wrap `step_executor.execute(...)` in try/except so *any* uncaught exception (a future stub, a Playwright crash, a bug) becomes a per-step `FAILED` result with `error_message`, never a sequence abort. This is the durable invariant the brief asks for in §3.1, and it's defense-in-depth: the executor *and* the runner both guarantee isolation.

---

## 3. Sync + async dual path (owner mandate) — design for maximum shared code

The owner wants **both** engines kept, sync fixed and async added, sharing as much as possible. The architectural challenge: `Step__Executor` is (by rule #16) the only class touching `page.*`, and it uses the **sync** API. The async engine needs `await page.*` on an async `Page`. The trick to maximal reuse is to recognise that **only the `page.*` call lines differ** — every other concern (parsing, validation, result-building, artefact bytes, orchestration, halt/deadline/status/timings) is engine-agnostic.

### 3.1 What is already engine-agnostic (shared, no change)
- **All schemas** (`Schema__Step__*`, `Schema__Sequence__Request/Response`, `Schema__Capture__Config`, artefact refs).
- **`Sequence__Dispatcher`** — parses `dict` → typed `Schema__Step__*`. Pure.
- **`Request__Validator`** — cross-schema validation. Pure.
- **`Artefact__Writer`** — operates on `bytes`; screenshot/PDF/HAR bytes are the same regardless of engine. Pure.
- **`JS__Expression__Allowlist`**, **`Capability__Detector`**, **`Credentials__Loader`** (the apply() call site differs sync/async, small).
- **Result builders** in `Step__Executor`: `passed_result`, `failed_result`, `skipped_result`, `resolve_id`, `filter_refs`, `now_ms`. Pure.

### 3.2 The refactor — extract the engine-neutral core, leave thin engine leaves

```
            ┌─────────────────────────────────────────────┐
            │  Step__Executor__Base   (NEW, engine-neutral)│  result builders, id/ref helpers,
            │   - passed/failed/skipped_result             │  the dispatch TABLE (action→method name),
            │   - resolve_id / filter_refs / now_ms        │  NotImplemented bookkeeping
            │   - dispatch(action) → handler name          │
            └───────────────┬───────────────┬─────────────┘
                            │               │
         ┌──────────────────▼──┐     ┌──────▼───────────────────┐
         │ Step__Executor      │     │ Step__Executor__Async    │   (NEW)
         │  (sync page.*)      │     │  (await page.*)          │
         │  execute_navigate:  │     │  execute_navigate:       │
         │   page.goto(...)    │     │   await page.goto(...)   │
         └─────────────────────┘     └──────────────────────────┘

            ┌─────────────────────────────────────────────┐
            │ Sequence__Runner__Base  (NEW, engine-neutral)│  the loop, halt_on_error, deadline→skip,
            │   - status derivation, timings, teardown      │  status/timings — ALL the orchestration logic
            └───────────────┬───────────────┬─────────────┘
                            │               │
         ┌──────────────────▼──┐     ┌──────▼───────────────────┐
         │ Sequence__Runner    │     │ Sequence__Runner__Async  │   (NEW)
         │  result = exec(...)  │     │  result = await exec(...)│
         │  launcher (sync)     │     │  launcher (async)        │
         └─────────────────────┘     └──────────────────────────┘

         Browser__Launcher (sync_playwright)   Browser__Launcher__Async (async_playwright)  (NEW)
            └── shared: build_launch_kwargs() (the chromium-args logic, pure) ──┘
```

- **Only the `execute_*` bodies and the `await`/launcher lines differ.** Everything structural is in the `*__Base` classes. This is the "as much common code as possible" the owner asked for — realistically ~85% shared.
- **`Step__Executor.execute` is currently an `if/elif` chain** (lines 61–72). Replace with a **dispatch table** (`{Enum__Step__Action.NAVIGATE: 'execute_navigate', …}`) in the base — cleaner, and *the same table drives both engines*. (Quality win + reuse.)
- **Routing:** add `POST /sequence/execute-async` (and, if cheap, `/screenshot-async`) returning the **identical** `Schema__Sequence__Response`, with a new `engine: Enum__Engine = "sync"|"async"` field so the Workbench can label runs (their §2.1 ask). The async route is `async def` and `await`s the async runner directly (no ThreadPoolExecutor needed — it's loop-native).

### 3.3 Boundary decision (Architect owns this)
CLAUDE.md **rule #16** ("`Step__Executor` is the ONLY class that calls `page.*`") must be amended to: *"the `Step__Executor` family (`Step__Executor`, `Step__Executor__Async`) are the only classes that call `page.*`; `Browser__Launcher`/`Browser__Launcher__Async` retain the lifecycle carve-out."* I will log this in the decisions log and the reality doc when the code lands. No other class gains `page.*` access.

### 3.4 Why not collapse to one engine (addressing the brief's §2.1 (c))
The brief proposes building both then deleting the loser. The owner has chosen to **keep both for now** — so we design the shared-core split so that *if* we later collapse, deleting one leaf (`*__Async` or the sync leaf) leaves the `*__Base` intact and the other engine fully working. The refactor makes both "keep both" and "collapse later" cheap.

---

## 4. Artefacts & capture semantics (§4 / §4.1)

The capture pipeline is the second-biggest gap. Today: only an explicit `screenshot` step (or `get_content` inline) produces an artefact; the rich `capture_config` is inert. The brief's §4.1 **hybrid model is correct and consistent with the existing (unimplemented) `screenshot_on_fail` field.** Plan:

1. **Self-describing artefact schema (§4).** Enrich the artefact ref returned in `step_results[].artefacts` / top-level `artefacts` to carry: `type, step_index (null=terminal), sink, content_type, encoding, size_bytes, filename`, plus `inline_b64` | `vault_ref` | `s3_ref` | `url`. `Artefact__Writer` already routes INLINE (real) / VAULT (seam) / S3 (seam) / LOCAL (real) — we enrich the *ref object*, not the writer's plumbing.
2. **Terminal + on-fail capture (§4.1 hybrid).** In the runner, after the step loop: if `capture_config.screenshot.enabled` → capture a terminal screenshot (`step_index=null`); if the sequence ended failed and `screenshot_on_fail.enabled` → capture on-fail; if `page_content.enabled` → capture final DOM. This is engine-neutral orchestration → lives in `Sequence__Runner__Base`.
3. **Document the inline size cap** and the default sink matrix (`screenshot=inline`, `video/har/trace=vault|s3`).
4. **`video`/`har`/`trace`/`console_log`/`network_log`** are context-level (must be wired at `browser.new_context(...)` time, not per-step). Phase 3 — needs the launcher to accept context options. This is where the async engine may actually be cleaner (Playwright's tracing/HAR APIs are ergonomic), informing the eventual sync-vs-async decision.

---

## 5. Capabilities, response typing, health, spec (§3.2/3.3/3.6/7.1)

- **Type the response (§3.2):** wire `Schema__Sequence__Response` as the route's `response_model`. The route returning `.json()` is the reason OpenAPI shows `string`. Also type `/screenshot`, `/health/*`.
- **Capabilities introspection (§3.3/§7.1):** make `GET /health/capabilities` return the **authoritative verb list with per-verb field schema**, supported `wait_until` states, screenshot formats, and sinks — sourced from the dispatch table + `Capability__Detector`. This is the single highest-leverage doc fix: the Workbench's "Live capabilities" panel renders it automatically, and it stops clients hand-maintaining a verb list that's currently *wrong* (lists unimplemented verbs).
- **Health (§3.6):** confirm a cheap `GET /health/status` returning `{version, status, browser_pool, uptime_ms}`. Document the three health groups (`/health/*` app-level, `/admin/*` agentic, `/info/*` framework).

---

## 6. Statelessness (§7.3) — mostly already true, audit the edges

`Browser__Launcher` is already per-request fresh + torn down. Audit items: (a) LOCAL_FILE artefact sink and any video/HAR/trace dirs must be swept on request completion (success *and* failure); (b) `credentials` applied to the context are never persisted; (c) a periodic `/tmp` sweep as a backstop on long-lived EC2. Add a regression test asserting no residual browser profile dirs / temp files after a run. Low effort, high trust.

---

## 7. CORS / TLS (§3.4/§3.5) — clarify the two access modes

There are **two ways** a client reaches the service, with different CORS owners:

1. **Through the vault `/pw` proxy** (the Workbench's actual deployment, `https://dev.vault.sgraph.ai` → `/pw/*`): CORS is answered by the **vault**, and we fixed it this session (`x-sgraph-access-token` in allow-headers, `ACAO:*`, OPTIONS 204). The Workbench should call `/pw/*` and this is already green.
2. **Directly to sg-playwright** on its own origin: CORS is minimal/absent. If the Workbench ever points at a raw instance, sg-playwright needs its own CORS middleware.

→ **Action:** document that the supported browser path is `/pw/*` (proxied). Optionally add a configurable CORS middleware to sg-playwright for direct access, mirroring the vault's allow-list. TLS: document that self-signed-on-raw-IP is expected; the proxied path already has a real cert via the vault.

---

## 8. New capabilities (§7) — triage

| Ask | Disposition |
|---|---|
| §7.1 capability introspection | **Phase 4** — do it; high leverage, low cost. |
| §7.2 native assertion steps (`expect_*`) | **Phase 5** — natural fit; implement as new verbs returning pass/fail. Sequence the verb set first. |
| §7.3 statelessness | **Phase 1** audit (above). |
| §7.4 `evaluate` allow-list docs | **Phase 4** — already enforced by `JS__Expression__Allowlist`; just document + clear error. |
| §7.5 network control, §7.6 retries, §7.9 per-step timings | **Phase 5** — additive; retries + per-step timings are cheap. |
| §7.7 trace artefact | **Phase 3** with HAR/video (context-level). |
| §7.8 idempotent `sequence_id` | **Phase 5** — needs a short-lived result cache; tension with strict statelessness — discuss (Q in 03). |
| §7.10 result streaming (SSE) | **Phase 5+** — pairs naturally with the async engine. |
| §7.11 live screencast, §7.12 CDP relay | **Explore / separate spike.** High interest but a different surface (websocket relay, lease lifecycle, teardown). Architecturally this belongs closer to the **`vnc`/`firefox` visible-browser specs** than to the stateless headless service — flag for a dedicated design rather than bolting onto `/sequence/execute`. |

---

## 9. Folded-in owner ask: prefix-agnostic `/pw` (default to `/pw` when unset)

Separate from the brief: make sg-playwright derive its mount prefix from the proxy's `X-Forwarded-Prefix` header (the reverse proxy already sends it), falling back to the `SG_PLAYWRIGHT__ROOT_PATH` env, **defaulting to `/pw` when neither is provided**. This removes the compose-side coupling (the prefix string stops being duplicated) and lets the same image sit behind any prefix without a rebuild. Folds into Phase 1 (small change to `Routes__Index` + the root_path middleware).

---

## 10. Phased plan (quality-first; each phase ships a rebuilt image + green regression run)

| Phase | Scope | Closes |
|---|---|---|
| **P0 — ground truth** | Rebuild `:latest` from HEAD; run the brief's §2 repro + the §6 regression checklist; record actual current behaviour. Wire typed `response_model`. | §3.2; establishes whether §2 is already fixed |
| **P1 — correctness (the real blocker)** | Implement missing verbs (`wait_for, press, select, hover, scroll, set_viewport, dispatch_event`); harden runner with per-step try/except; dispatch-table refactor; document `halt_on_error`; prefix-agnostic `/pw`. | §2b, §3.1, §3.3 (impl), §9 |
| **P2 — async engine (owner mandate)** | Extract `Step__Executor__Base` + `Sequence__Runner__Base`; add `Step__Executor__Async`, `Sequence__Runner__Async`, `Browser__Launcher__Async`; add `POST /sequence/execute-async`; `engine` marker. | §2.1 |
| **P3 — artefacts** | Self-describing artefact objects; terminal + on-fail + page_content capture (hybrid §4.1); inline cap + sink matrix; then context-level video/har/trace. | §4, §4.1 |
| **P4 — discoverability** | `/health/capabilities` with real verb schemas; documented health surface; `evaluate` allow-list docs; CORS-for-direct (optional). | §3.3, §3.6, §7.1, §7.4, §3.4 |
| **P5 — expressiveness** | Native assertion verbs; retries; per-step timings; network control; idempotency; (SSE streaming). | §7.2, §7.5, §7.6, §7.9, §7.8 |
| **Spike** | Screencast + CDP relay design (likely a separate spec, not this service). | §7.11, §7.12 |

**Regression suite (§6) becomes CI** in the image repo (the brief's §6 ask) — gated so a new `:latest` is only published if all verbs, artefact round-trip, isolation, halt, timeout, concurrency, and CORS checks pass. This is the "trust new versions on sight" the brief wants and the quality bar the owner mandated.

---

## 11. Quality / cleanup register (the owner's "improve this code" mandate)

Concrete improvements to bank during the above, beyond fixing bugs:

1. **Dispatch table over `if/elif`** in the executor (P1) — also kills the silent gap where an unmapped action would mis-route.
2. **No shipping `NotImplementedError` stubs** in a critical path — either implement or remove from the advertised verb set (P1). A stub that aborts the caller's whole request is worse than an absent verb.
3. **Runner exception isolation** as an explicit invariant with a test (P1).
4. **Engine-neutral base extraction** (P2) removes the architectural pressure that would otherwise duplicate orchestration logic across sync/async.
5. **Typed responses everywhere** (P0/P4) — every route returns a `.json()` on a typed schema *and* advertises it as `response_model` (closes the "OpenAPI says string" class of issue across the surface, not just `/sequence/execute`).
6. **Capability source of truth** — verbs/sinks/formats derived from one registry feeding both the dispatcher, the validator, and `/health/capabilities` (P4) — so the spec can never drift from behaviour again (this drift is exactly what bit the Workbench team).
7. **Temp-file lifecycle test** (P1/P6) — assert statelessness, don't assume it.
8. **Comment the `_run_sequence_via` guard** more loudly and add a test that exercises the loop-detected branch — it's subtle and load-bearing.

---

## 12. What I need from the owner to proceed

1. **Confirm the phasing / priority** (esp. that P1 verbs precede P2 async — the verbs are the real blocker; the async path is the mandate but not the thing stopping the Workbench today).
2. **Confirm scope of P2 one-shots** — async variants of `/browser/*` and `/screenshot` too, or just `/sequence/execute-async`?
3. **Screencast/CDP (§7.11/7.12):** treat as a separate spec spike (my recommendation) or in-scope here?
4. Answers to the questions in `03__questions-for-the-workbench-agent.md` (some are for the Workbench team, some for you).
