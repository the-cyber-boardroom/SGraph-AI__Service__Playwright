# Debrief — Milestone — 100%-clean-state per call + timing breakdown surfaced

- **Date:** 2026-04-17
- **Commit(s):** `906ba05` (refactor + tests + reliability), preceded by `8922484` (payload caps), `cdba60c` (sandbox flags), `22dd98a` (`browser.contexts` property fix), `6869632` (timeout_ms=0 guard).
- **Trigger:** Production tests of `/quick/html` and `/quick/screenshot` against `https://www.google.com` and `https://send.sgraph.ai` surfaced four cascading bugs (Swagger-default `timeout_ms=0`, `'list' object is not callable`, `TargetClosedError`, 64 KB payload cap). After all four were fixed, the user asked: *"should we have issues when running lots of calls to the same lambda function (i.e. chrome crashing)"*. The follow-up redirect was definitive: *"i think we should have 100% clean state between requests"* + *"can you also capture those stats on the return data?"*.
- **Status:** Deployed; verified live behind CloudFront (`https://dev.playwright.sgraph.ai`).

## What was delivered

### Per-call sync_playwright + Chromium

`Browser__Launcher.launch()` no longer keeps a singleton `sync_playwright` runtime. Every call now:

1. Starts a **fresh** `sync_playwright` Node subprocess (~420 ms cold).
2. Launches a **fresh** Chromium with the spec §5.2 default flags (`--no-sandbox --disable-gpu --disable-dev-shm-usage --single-process --use-mock-keychain`) — ~130 ms.
3. Returns a typed bundle: `Schema__Browser__Launch__Result(browser, playwright, playwright_start_ms, browser_launch_ms)`.

`register(session_id, result)` stashes both handles together. `stop(session_id)` closes the Browser and stops the sync_playwright subprocess, returning the close duration. The two are inseparable — there is no path that closes one without the other.

### try/finally teardown in Sequence__Runner

`Sequence__Runner.execute()` wraps the entire step loop in try/finally. When `close_session_after=True` (the default for every Quick endpoint), `browser_launcher.stop(session_id)` is guaranteed to run even if a step raises. The launcher registry is empty after every stateless request — no zombie Chromium, no leaked Node subprocess, no stuck handle.

### Timing breakdown surfaced to callers

New `Schema__Sequence__Timings` block on every sequence response:

| Field | What it measures |
|---|---|
| `playwright_start_ms` | `sync_playwright().start()` — Node subprocess boot |
| `browser_launch_ms` | `chromium.launch()` — Chromium process boot |
| `steps_ms` | Wall clock across the step loop |
| `browser_close_ms` | `browser.close() + playwright.stop()` |
| `total_ms` | Outer wall clock (always ≥ sum of others) |

- `/sequence/execute` → JSON field `timings` on `Schema__Sequence__Response`.
- `/quick/html` → JSON field `timings` on `Schema__Quick__Html__Response`.
- `/quick/screenshot` → HTTP response headers `X-Playwright-Start-Ms`, `X-Browser-Launch-Ms`, `X-Steps-Ms`, `X-Browser-Close-Ms`, `X-Total-Ms` (raw PNG body leaves no room for JSON).

### Schemas added

- `schemas/browser/Schema__Browser__Launch__Result` — return shape of `Browser__Launcher.launch()`.
- `schemas/sequence/Schema__Sequence__Timings` — per-phase wall-clock breakdown.
- `schemas/quick/Schema__Quick__Screenshot__Result` — internal holder (`png_bytes` + `timings`) so the route can emit headers alongside the raw image body.

### Payload-size primitives (preceded the milestone but underpin it)

- `Safe_Str__Page__Content` — 10 MB cap on HTML returned by `GET_CONTENT`.
- `Safe_Str__Artefact__Inline` — 20 MB cap on inline artefact base64 payloads (typical PNG ≈ 100 KB; large pages ≈ 100 KB – 5 MB; both blew the 64 KB `Safe_Str__Text__Dangerous` default).

## Production verification

Three back-to-back `/quick/screenshot` runs from the user's session (CloudFront → Lambda → Chromium):

| Run | playwright_start | browser_launch | steps | browser_close | total |
|---|---|---|---|---|---|
| 1 — content page    | 420 ms | 132 ms | 441 ms | 142 ms | 1164 ms |
| 2 — same page       | 420 ms | 126 ms | 414 ms |  52 ms | 1039 ms |
| 3 — 404 page        | 414 ms | 128 ms | 180 ms |  49 ms |  800 ms |

Reading the numbers:
- **sync_playwright start ~420 ms** is the fixed cost of fresh-per-call state. Identical across runs → no warm-up cheat happening.
- **Chromium launch ~130 ms** — small thanks to `--no-sandbox --single-process` + Lambda's local disk.
- **steps_ms** tracks page complexity (404 fastest, as expected).
- **Total ~800–1200 ms** — the overhead of 100% isolation is ~550 ms; the rest is real work.

The 64 KB payload bug, the `'list' object is not callable` bug, and the `TargetClosedError` are all confirmed gone — the user's earlier *"btw, previous deployment worked :)"* (with an SG/Send screenshot rendered in Swagger) closed the loop on those. The screenshot timing run above closed the loop on the clean-state refactor.

## Tests

- **`tests/unit/service/test_Sequence__Runner.py`** — 4 new cases:
  - Ad-hoc sequence populates all five timing fields.
  - Reused session reports zero boot timings.
  - 20 sequential ad-hoc requests leave the launcher registry empty (`launched == 20`, `len(stopped) == 20`).
  - Teardown runs even when a step raises.
- **`tests/unit/service/test_Browser__Launcher.py`** — register/stop signature updated to `Schema__Browser__Launch__Result`; healthcheck assertion updated (no more singleton `playwright_started` flag).
- **`tests/integration/service/test_Browser__Launcher.py`** — every test updated to the new launch-result shape; new assertion that `r1.playwright is not r2.playwright` (independent Node subprocesses).
- **All 7 unit `_FakeLauncher` classes** updated to return `Schema__Browser__Launch__Result` and a `_FakePlaywright` stand-in with a `stop()` no-op.
- **Result:** 306/306 unit tests pass locally (fast_api routes tests need Python 3.12 — verified in CI).

## Failures & lessons (good-failure / bad-failure convention)

### Good failures (caught early, informed design)

- **Singleton sync_playwright was the obvious first design.** Rejected after the user's redirect to "100% clean state". Cost: ~30 minutes of design talk before any code changed. Saved: a debugging session 6 months from now when proxy state from a previous request leaked into a sensitive scrape.
- **`Browser.contexts` looked like a method.** Three call sites in service code, plus eight test fakes that mirrored the wrong shape. Caught by the very first production deploy; the fix added `@property` to all eight fakes so the bug *can't* slip back in via a green test suite.
- **Swagger renders integer defaults as 0.** `timeout_ms=0` was zeroing every step's per-action timeout. Caught the moment a real caller hit the endpoint with the auto-filled body. Fix is one line (`if timeout_ms is not None and int(timeout_ms) > 0`) but the lesson — *"Swagger defaults are user input, not framework noise"* — applies broadly.
- **64 KB `Safe_Str__Text__Dangerous` cap was invisible until real data hit it.** Real PNGs are ~100 KB; real page HTML can be 5 MB. Two new project-local primitives (`Safe_Str__Page__Content` 10 MB, `Safe_Str__Artefact__Inline` 20 MB) lift the cap without weakening the dangerous-content regex.

### Bad failures (none worth flagging this slice)

The original error format silenced every traceback to `"{Type}: {msg}"` via `osbot-fast-api`'s `Type_Safe__Route__Wrapper`. That was fixed mid-slice by wrapping `quick_html` / `quick_screenshot` bodies in try/except that emit `HTTPException(502, …)` with the last 1800 chars of traceback. Without that, every subsequent debug round would have cost another deploy cycle.

## Deviations from brief

- The reality doc and routes catalogue describe `Sequence__Runner` and the Quick endpoints, but they never specified per-phase timings on the response. Added by user request mid-slice ("can you also capture those stats on the return data?"); the new `Schema__Sequence__Timings` is now part of the contract surface.
- `Schema__Quick__Screenshot__Result` is an internal-only holder (route → service handshake). It is **not** a wire schema — `/quick/screenshot` still returns raw `image/png`. Listed under `schemas/quick/` for one-class-per-file consistency.

## Follow-ups

- **Reality doc bump to v0.1.13** — capture the new schemas, the new timing surface, and the production-verified clean-state contract. (Done in same commit batch as this debrief.)
- **Decisions log** — record the "100% clean state per call" decision so a future maintainer doesn't try to "optimise" by re-introducing a singleton sync_playwright.
- **Phase 2.11 (deferred Step__Executor handlers)** — 10 step actions are still NotImplementedError stubs. The clean-state contract makes them safer to add, since each call gets a fresh browser regardless of action set.
- **Cold-start optimisation (later)** — if ~550 ms fixed overhead becomes painful, options to investigate (in priority order): (a) Lambda provisioned concurrency to keep Node warm at the runtime level, (b) browser pre-warm via a one-shot launch on Lambda init that stays *unused* by handlers but keeps the binary cached, (c) a connection-pooling provider (BROWSERLESS / CDP_CONNECT) for high-volume callers willing to give up clean state. None of these should be touched until a real workload demands it — the current 800–1200 ms total is well inside the 30 s API Gateway ceiling.
- **Per-step timings inside `steps_ms`** — could add `Schema__Step__Result__Base.duration_ms` aggregation so callers can spot the *one* slow step in a long sequence. Not requested yet; flagged for when sequence callers start hitting timeouts.
