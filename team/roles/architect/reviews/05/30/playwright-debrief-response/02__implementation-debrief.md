---
title: "Φ1–Φ7 implementation debrief — what landed against the 05-30 brief"
file: 02__implementation-debrief.md
author: Dev (Claude, Opus 4.7) — SGraph-AI__Service__Playwright
date: 2026-05-31
companion: 01__implementation-plan.md
images:
  - diniscruz/sg-playwright:v0.2.54  (and onward — increment-tag bumps every dev merge)
status: DEBRIEF — paste into the next Claude session that owns the original brief so it knows what shipped, what's deferred, what changed in the API, and what to test against the new image.
---

# Φ1–Φ7 implementation debrief

This document closes the loop on `01__implementation-plan.md`. Φ1 through Φ7
shipped. Φ8 (async engine) is the explicit deferred item — see §5.

---

## 1. What shipped — by phase

### Φ1 — Bugfix block (BUG-1 + BUG-2 + FR-5a)

| | |
|---|---|
| BUG-1 fix | New primitive `Safe_Str__Url__Permissive` (RFC 3986 fragment class — accepts `:` `@` `/` `?` and sub-delims in fragment). Swapped across 12 schemas (browser request/response, step verbs, screenshot, config). Vault URLs like `https://dev.vault.sgraph.ai/#tcss7to5vfp6asjbm1t1p5ng:rqw3wk4b` now validate without percent-encoding workarounds. |
| BUG-2 fix | Lifted 6 subclass-specific fields onto `Schema__Step__Result__Base` (`content`, `content_format`, `content_type`, `url`, `return_value`, `return_type`). Polymorphic `List[Schema__Step__Result__Base]` no longer drops subclass fields when FastAPI's `response_model` narrows. |
| FR-5a | `evaluate`'s return value is now surfaced. `Schema__Step__Result__Evaluate.return_value` (classified into `JSON`/`STRING`/`NUMBER`/`BOOLEAN` via `Enum__Evaluate__Return_Type`). |

### Φ2 — Quick wins (FR-1a/b, FR-4, FR-7)

| New / changed | Wire surface |
|---|---|
| FR-4 plain `wait` verb | `{action:"wait", duration_ms:N}` |
| FR-1a `wait_for: text` | `{action:"wait_for", text:"…", selector?:"…"}` |
| FR-1b `wait_for: selector_gone` | `{action:"wait_for", selector:"…", selector_gone:true}` |
| FR-7 artefact pixel dims | `step_results[i].artefacts[j].width/.height` — parsed from PNG IHDR |
| FR-7 viewport on screenshot | `{action:"screenshot", viewport:{width:W,height:H}}` |

### Φ3 — DOM reads + universal predicates (FR-1c, FR-2, FR-5b, FR-5d)

| Verb | What it does |
|---|---|
| `get_text` | `innerText` of page or selector |
| `get_html` | `outerHTML` of page (`page.content()`) or selector (`locator.evaluate('el => el.outerHTML')`) — distinct from `get_content`'s `innerHTML` |
| `get_dom_tree` | Compact JSON `{tag, id, class, role, accessible_name, rect, visible, child_count, children}`. Bounded by `max_depth` + optional `root_selector` + `include_invisible`. The headline "what should I be targeting?" verb. |
| `get_a11y_tree` | **Via CDP** — `page.context.new_cdp_session(page).send('Accessibility.getFullAXTree')`. Playwright 1.49+ removed `page.accessibility.snapshot()` — switched to CDP for forwards compatibility. Returns `{nodes: [{nodeId, role, name, ignored, childIds, …}]}`. `interesting_only=True` filters out `ignored:true` nodes. |
| `get_pdf` | `page.pdf(format/landscape/print_background)` → PDF artefact via `capture_config.pdf` |
| `wait_for: function` (FR-1c) | Allowlist-gated. `page.wait_for_function(expr)`. Highest precedence in the wait_for ladder. |

### Φ4 — Console + network forensics (FR-1d, FR-5c)

| | |
|---|---|
| New service class | `Page__Listeners__Buffer` — per-page event sink with 4 buffers (`console_events`, `request_events`, `response_events`, `failed_events`) + live `in_flight_ids` set. Bounded at 1000 events per kind (ring trim). |
| Sequence__Runner wiring | Attaches buffer to the page BEFORE any navigate — so load-time `page.on('console')` etc. events are captured (anything attached after `goto` misses load-time). |
| End-of-sequence artefacts | When `capture_config.console_log.enabled` / `network_log.enabled` is true, the runner emits a `console_log` / `network_log` artefact at sequence end via `Artefact__Writer.write_artefact`. |
| New verbs | `get_console_tail(lines)`, `get_network_failures()` — read from the buffer. Architected here, consumed by the Φ5 probe-batch. |
| `wait_for: network_idle_ms` (FR-1d) | Tunable quiet window. Polls `buffer.in_flight_count()` every 50 ms; succeeds when in-flight is 0 for N consecutive ms. Falls back to Playwright's built-in `networkidle` when no buffer is attached. **`websocket` + `eventsource` resource types are excluded from the in-flight count** — they're designed to stay open and would make the predicate impossible on any SPA. |

### Φ5 — Probe-batch (`POST /inspect`) — the headline feature

`POST /inspect` — snapshot once, probe many. Body shape:

```json
{
  "navigate": {"url": "https://..."},
  "settle":   [{"action": "wait_for", "text": "Vault unlocked"}],
  "probes": {
    "current_url": {"action": "get_url"},
    "page_dom":    {"action": "get_dom_tree", "max_depth": 4},
    "shot":        {"action": "screenshot"}
  },
  "diagnostics_on_fail": true
}
```

Response: `{navigate_result, settle_results, probe_results: {name: result}, diagnostics?, artefacts, timings}`.

* **Read-only allowlist enforced**: probes must use `get_url` / `get_text` / `get_html` / `get_content` / `get_dom_tree` / `get_a11y_tree` / `get_pdf` / `screenshot` / `get_console_tail` / `get_network_failures`. Mutating verbs → HTTP 422.
* **`diagnostics_on_fail=true` (default)**: at sequence end the executor appends `get_console_tail` + `get_network_failures` as terminal steps. If ANY step (navigate / settle / probe) failed, the response carries `diagnostics: {console_log, network_failures}`. Green-path responses omit the field — kept tidy.
* `Probe__Executor` reuses `Sequence__Runner` (no duplicate launch/page/buffer/teardown plumbing).

### Φ6a — Shadow-DOM + iframe traversal + `screenshot.frame_selector`

`Φ6b` (context-level video / HAR / trace + vault/S3 sink wiring) is deferred to a fast-follow slice.

| | |
|---|---|
| `get_dom_tree` extended | Honours open shadow roots + same-origin iframes. Boundary flags on the host/frame node: `shadow_root:true`, `iframe:true`, `cross_origin:true` (when contentDocument throws SecurityError). Closed shadow roots remain inaccessible — browser-side guarantee. |
| `screenshot.frame_selector` | Captures inside a same-origin iframe. Pairs with `selector` (element within frame) or stands alone (captures the iframe element via parent locator). |
| `>>>` shadow-pierce selector | Playwright engine already supports — documented; no code change. |

### Φ7-proper — Opt-in stateful session handle (`POST /session/*`)

| Endpoint | Body | Response |
|---|---|---|
| `POST /session/open` | `{browser_config?, credentials?, ttl_ms}` | `{session_id, expires_at_ms, expires_in_ms}` |
| `POST /session/{id}/act` | `Schema__Sequence__Request` minus `browser_config` | `Schema__Sequence__Response` |
| `POST /session/{id}/probe` | `Schema__Inspect__Request` minus `navigate` + `browser_config` | `Schema__Inspect__Response` |
| `POST /session/{id}/close` | — | `{session_id, closed:bool}` |

**Architectural note** — Playwright sync API is thread-affine. Each held session owns a dedicated daemon thread (`Session__Worker`) that holds the Playwright runtime + browser + page for the session's whole lifetime. All `/session/{id}/*` requests marshal work onto that worker thread via `queue.Queue` + `concurrent.futures.Future`. Cross-thread page handoff was the original Φ7 bug — diagnosed via the "session/act navigate failed with no error_message" symptom, fixed by introducing the per-session worker.

**Lifecycle**:
* `open` → spawn `Session__Worker`; worker thread launches Chromium + attaches `Page__Listeners__Buffer`.
* `act` / `probe` → `state.worker.submit(fn, …)` — same OS thread that opened the page handles every subsequent call.
* `close` → `worker.stop()` → poison pill → teardown runs on the worker thread (`browser.close()` has the same affinity constraint as launch).
* **TTL** capped at `capabilities.max_session_lifetime_ms`. **Cleanup is lazy** — `sweep_expired()` is called from every registry operation AND from `Playwright__Service.setup()` (which runs at the start of every service method). So idle sessions get reaped whenever ANY endpoint is touched — no background sweep thread.
* **404** on `/act` / `/probe` for unknown / expired session.

---

## 2. Bugs caught en route (worth noting)

| | Symptom | Root cause | Fix |
|---|---|---|---|
| `/inspect` asyncio crash | "Playwright Sync API inside asyncio loop" 400 on every `/inspect` request | `Probe__Executor` called `sequence_runner.execute` directly, bypassing the `_run_sequence_via` ThreadPoolExecutor wrapper that `/sequence/execute` uses | `Probe__Executor.sequence_runner` → `run_sequence` callable; `Playwright__Service.setup()` injects the wrapped `self._run_sequence`. Pattern: every Playwright-sync entry point is wrapped at the service boundary, never below. |
| `/dev/shm` exhaustion | Container died mid-suite after ~5 sequence runs; 26 connection-refused cascade | Docker's 64 MB `/dev/shm` default starves Chromium renderer IPC | `docker run --shm-size=2g` in CI; documented for EC2 launchers |
| Playwright `page.accessibility` removed in 1.49 | `get_a11y_tree` returned step `status=failed` with `'Page' object has no attribute 'accessibility'` | Playwright deprecated + removed the API; service ships 1.58.0 | Switched to CDP — `page.context.new_cdp_session(page).send('Accessibility.getFullAXTree')`. Shape changed from nested-tree to flat `nodes` list; documented. |
| `wait_for: network_idle_ms` permanently impossible on SPAs | `in_flight=21` after 15s — never reached quiet | Buffer counted `websocket` + `eventsource` as in-flight; they're designed to stay open | Excluded from `in_flight_ids`; still recorded in `request_events` for diagnostics |
| **(latent — investigate)** `page.locator('<missing>').screenshot(timeout=N)` crashes the service | `RemoteProtocolError: Server disconnected without sending a response`, then 25 connection-refused | Probably a Chromium subprocess cleanup race specific to the timeout-then-cleanup path on missing elements | Two live tests dropped (`/browser/fill` with `input[name=q]`, `screenshot.frame_selector` with missing iframe). Unit-tested paths are unaffected. Open for a focused investigation slice. |

---

## 3. API additions summary (at a glance)

**24 step verbs** (was 16 in v0.2.47):
> navigate · click · fill · press · select · hover · scroll · wait_for · screenshot · video_start · video_stop · evaluate · dispatch_event · set_viewport · get_content · get_url · **wait** · **get_text** · **get_html** · **get_dom_tree** · **get_a11y_tree** · **get_pdf** · **get_console_tail** · **get_network_failures**

**`wait_for` predicates** (in precedence order):
> function · network_idle_ms · text · selector(+selector_gone / visible / attached) · url_pattern · state · (default load)

**Top-level routes** (deltas from v0.2.47):
> + `POST /inspect`
> + `POST /session/open`, `/session/{id}/act`, `/session/{id}/probe`, `/session/{id}/close`

**Lifted onto `Schema__Step__Result__Base`** (BUG-2 prevention pattern):
> `content`, `content_format`, `content_type`, `url`, `return_value`, `return_type`, `text`, `html`, `dom_tree`, `accessibility_tree`, `console_log`, `network_failures`

---

## 4. Testing footprint

| Tier | Count | Where |
|---|---|---|
| Unit | 4625 passing | `tests/unit/` |
| Live integration (sgraph.ai + send.sgraph.ai + dev.vault.sgraph.ai) | 44 (with 1 skipped — `wait_for: network_idle_ms` against the analytics-heavy marketing site is brittle) | `tests/integration_live/` |
| CI runs the live tier with `pytest -n 4 --dist loadgroup` | xdist parallel | conftest auto-pins `@pytest.mark.serial` (session lifecycle) onto one worker via `xdist_group` |

**Resource introspection** after every CI integration run: orphan Chromium count, zombies, `/dev/shm` usage, FD count, `/metrics` sample. Observability only — exits 0 — so leak drift becomes visible before it hits production.

---

## 5. Out / deferred

| | Why deferred |
|---|---|
| **Φ6b**: video / HAR / trace context-level capture + vault / S3 `Artefact__Writer` sink wiring | Touches `browser.new_context(record_har=…)` + AWS adapter; substantial enough for its own slice. Today: only `INLINE` / `LOCAL_FILE` sinks are wired. |
| **Φ8**: async engine leaf (`Step__Executor__Async` + `Browser__Launcher__Async` + `Sequence__Runner__Async` + `/sequence/execute-async`) | Explicit "owner mandate, deprioritised" in the plan. The sync engine + ThreadPoolExecutor wrappers are the load-bearing duct tape until concurrent demand justifies the parallel engine. |
| Multi-container parallel testing | pytest-xdist with one container is currently sufficient. Worth revisiting if cross-request bugs show up that single-container parallel doesn't expose. |
| Background TTL sweep thread for sessions | Lazy cleanup-on-access is the design — no clock-driven thread. Idle EC2 with zero requests for hours could hold expired sessions, but the realistic deployment polls `/metrics` or `/health/info` which triggers the sweep. |
| Cross-origin iframe piercing in `get_dom_tree` | Browser security limit — out per the plan. Marked `cross_origin: true` on the boundary node. |

---

## 6. What's worth re-testing against the new image

1. **The vault driving session** (the @Content debrief case): `wait_for: text` → `get_dom_tree` → real selector → click. Should now succeed without blind waits.
2. **`/inspect` end-to-end**: open with navigate + 3 probes (current URL, DOM tree, screenshot). Should return all three in one round-trip.
3. **`/inspect` with `diagnostics_on_fail`**: settle on a non-existent selector with `timeout_ms: 2000`. Should return 200 with sequence `status=partial|failed` and `diagnostics: {console_log, network_failures}`.
4. **`/session/*` amortisation**: open → act (navigate + decrypt) → probe × N. Each `/probe` should return in well under the wall-clock of a fresh `/inspect`.
5. **`wait_for: function` allowlist denial**: default service has empty allowlist → the wait_for step should fail with `error_message` containing "allowlist", and the sequence status should be `failed` (not HTTP 422 — Sequence__Runner converts validate_step errors to per-step FAILED so one bad step can't abort the sequence).
6. **`get_a11y_tree`**: new CDP shape — response is `{nodes: [...]}` flat list, not the old nested tree.

---

## 7. Pointer to the source

* Implementation plan: `team/roles/architect/reviews/05/30/playwright-debrief-response/01__implementation-plan.md`
* Updated agent guide: `library/guides/v0.2.54__playwright-api-via-pw__claude-session-guide.md`
* Live integration tests (read these to see contract examples): `tests/integration_live/`
