---
title: "Original brief (verbatim) — sg-playwright, from the Playwright Workbench team"
source: incoming brief from the agent building the Playwright Workbench tool
captured: 2026-05-29
note: "Reproduced verbatim for the dev-pack record. Accuracy of its claims about the CURRENT code is assessed in 01__architecture-and-implementation-review.md."
---

# sg-playwright — Briefing for the Service Maintainer

**From:** the team building the **Playwright Workbench** (a vault-resident QA tool that drives `sg-playwright` over its `/pw/*` REST API)
**Target service:** `Fast_API__Playwright__Service` — currently **v0.38.0**
**Date:** 2026-05-29
**Priority order:** (1) blocking bug, (2) reliability/observability, (3) new capabilities

---

## 1. What we are building and why it matters to you

We are building a **QA testing tool that uses Playwright**. It is a browser-based app that lets a human (or another agent) compose, run, save, and replay multi-step browser automation **sequences** against arbitrary target websites, entirely by calling your `/pw/*` API. Everything we do is an HTTP request to your service; we hold no Playwright ourselves.

The app has these surfaces, all of which call your API:

- **Composer** — build an ordered list of steps (navigate, click, fill, screenshot, …), run the whole thing or "run to step N", and view per-step results + artefacts.
- **Playground** — fire single one-shot calls (`/browser/*`, `/screenshot`).
- **Runner** — stored scenarios with assertions (URL/title/selector/status checks) and run history.
- **Targets** — a registry of `sg-playwright` endpoints (base URL + access token); the active one is what every page talks to.
- **Health** — hits your health/capability endpoints.

Because the tool is generic and will be pointed at **increasingly complex real-world workflows** (multi-page journeys, logins, form flows, regression suites), the reliability and expressiveness of your API is the single biggest determinant of whether this tool is useful. The asks below are ordered accordingly.

**How we call you:** `POST {baseUrl}/sequence/execute` with header `x-sgraph-access-token: <token>`, `Content-Type: application/json`. Steps are sent **flat** (fields at the top level of each step object), which matches your `Schema__Sequence__Request__BaseModel.steps` being `additionalProperties: true`:

```json
{
  "steps": [
    { "action": "navigate", "url": "https://example.com", "wait_until": "load" },
    { "action": "screenshot", "full_page": true }
  ],
  "capture_config": { "screenshot": { "enabled": true, "sink": "inline" } }
}
```

---

## 2. BLOCKING BUG — screenshot (and likely any artefact-producing step) crashes the whole sequence

**This is the top priority.** Any sequence that includes a `screenshot` step fails with HTTP 400 and this body:

```json
{ "detail": "Error: It looks like you are using Playwright Sync API inside the asyncio loop.\nPlease use the Async API instead." }
```

### Evidence (captured from real runs)

| Sequence sent | Result |
|---|---|
| `[navigate]` | **200 OK** — `status: "completed"`, `steps_passed: 1` |
| `[navigate, wait_for, screenshot]` | **400** — the sync-API-in-asyncio-loop error above |
| `[navigate, wait_for, screenshot, evaluate, get_url]` | **400** — same error |

So `navigate` alone is fine; **introducing a `screenshot` step rejects the entire sequence** (no steps run, no artefacts returned). The request body is valid and you accept its shape — the failure is at execution time.

### Root cause (our read)

Somewhere in the request path you are running under an **async event loop** (FastAPI async route / asyncio), but the screenshot handler calls Playwright's **sync** API (`sync_playwright()` / `page.screenshot()` on the sync `Page`). Playwright explicitly forbids the sync API inside a running asyncio loop and raises exactly this message.

### What we need

1. **Make the execution path consistently async.** Use `async_playwright()` and `await page.screenshot(...)`, `await page.goto(...)`, etc. — OR run the sync Playwright work in a dedicated worker thread / process that has **no** running asyncio loop (e.g. `await anyio.to_thread.run_sync(...)` / a `ProcessPoolExecutor`). Pick one model and apply it to **every** step handler, not just screenshot.
2. **Audit all step verbs for the same latent bug.** `screenshot` is the one we hit because it's common, but `video`, `pdf`, `har`, `trace`, `get_content`, and `evaluate` may share the path. Please verify each verb runs end-to-end under load, not just `navigate`.
3. **Never let one step's exception 400 the whole sequence by default.** See §3.1 — a step failure should be reportable per-step.

### How to verify the fix

```bash
TOKEN=<access-token>
BASE=https://<host>/pw

# (a) the exact repro — must return 200 with an inline screenshot artefact
curl -sk -X POST "$BASE/sequence/execute" \
  -H "x-sgraph-access-token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"steps":[{"action":"navigate","url":"https://example.com"},{"action":"screenshot","full_page":true}],
       "capture_config":{"screenshot":{"enabled":true,"sink":"inline"}}}' | jq '.status, .steps_passed, (.step_results[].artefacts | length)'
# expect: "completed", 2 (or steps_passed match), and a non-zero artefact count on the screenshot step

# (b) one-shot screenshot endpoint
curl -sk -X POST "$BASE/screenshot" \
  -H "x-sgraph-access-token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","full_page":false,"format":"png"}' | jq 'keys'
```

A green result is: HTTP 200, `status: "completed"`, the screenshot step `status: "passed"`, and **a populated `artefacts` array** (see §4 for the artefact contract we need).

### 2.1 Ship a side-by-side **async** execute endpoint alongside the current one (don't replace — run both)

Rather than betting the existing endpoint on a single rewrite, please **stand up a parallel set of execution routes that use the async Playwright API internally**, living next to the current (sync) ones. For example:

- `POST /sequence/execute`        — current implementation (sync internally), left as-is
- `POST /sequence/execute-async`  — same request/response contract, but `async_playwright()` + `await` internally

(Apply the same pattern to the one-shots where useful: `/browser/navigate-async`, `/screenshot-async`, etc.) Keeping the **request and response schemas identical** between the two is the key requirement — our client can then switch which one it calls with a single config flag and compare like-for-like.

Why side-by-side rather than a straight replacement:

- **(a) Empirical comparison.** We can run the *same* real-world sequences against both and see which is more reliable and faster under actual usage (concurrency, big pages, long flows) — instead of guessing which model wins.
- **(b) A fallback when we hit the next async-class error.** The current sync path crashes on `screenshot` (the asyncio-loop error). If the async path has its *own* sharp edges on some other verb, having both means we always have a working route to fall back to per-verb, rather than being fully blocked.
- **(c) It de-risks the migration.** Once real usage shows a clear winner, you refactor to the survivor and delete the other — see the note below.

This is explicitly fine to do as a **proliferation of routes / experiments at this stage**: it's an ephemeral EC2 instance behind an API key, so adding parallel endpoints carries little risk. Once we know which execution model is robust across our workflows, it can be refactored and cleaned up (collapse back to a single `/sequence/execute`, drop the loser). We'd rather have two working-ish options now and consolidate later than one rewrite that might trade one async bug for another.

If it's cheap, a tiny marker in each response (e.g. `"engine": "sync" | "async"`) would let us label runs in our history and attribute reliability differences correctly.

---

## 3. Reliability & correctness (needed before complex workflows)

### 3.1 Per-step error isolation + a documented `halt_on_error` contract

Today a single failing step appears to abort the whole request at the HTTP layer (400, empty body). For real suites we need:

- Each step result to carry its own `status` (`passed`/`failed`/`skipped`) and `error_message`, **even when a step throws** — the HTTP call should still return **200** with a populated `step_results`, and the failing step marked `failed`.
- `sequence_config.halt_on_error: true` → stop at the first failed step, mark the rest `skipped`. `false` → run them all. (The field exists in the schema; please confirm it behaves this way and document it.)
- Reserve non-2xx HTTP codes for **request-level** problems (bad auth, malformed body), not for in-page step failures.

### 3.2 Stable, documented response schema

The 200 response we see today (good — please keep it stable and put it in the OpenAPI `responses`, which is currently just `"string"`):

```json
{
  "sequence_id": "safe-id_xxxx",
  "trace_id": "141ee092",
  "status": "completed",
  "total_duration_ms": 1472,
  "steps_total": 1, "steps_passed": 1, "steps_failed": 0, "steps_skipped": 0,
  "step_results": [
    { "step_id": "0", "step_index": 0, "action": "navigate",
      "status": "passed", "duration_ms": 817, "error_message": null, "artefacts": [] }
  ],
  "artefacts": [],
  "timings": { "playwright_start_ms": 518, "browser_launch_ms": 82, "steps_ms": 865, "browser_close_ms": 6, "total_ms": 1472 }
}
```

Asks:
- **Type the 200 response** in the OpenAPI spec (define `Schema__Sequence__Response__BaseModel`) so clients can generate against it. Right now `/sequence/execute` 200 is `application/json: "string"`.
- Keep `step_results[].action` populated (it is today — good; we rely on it to map results back to the steps we sent).
- Confirm whether artefacts attach to **`step_results[i].artefacts`**, the **top-level `artefacts`**, or both, and document the rule.

### 3.3 Document the step verb vocabulary in the spec

`steps` is `additionalProperties: true`, so the actual verb set and each verb's fields are invisible to clients. We currently maintain a hand-written list (`navigate, click, fill, press, select, hover, scroll, wait_for, screenshot, evaluate, get_content, get_url, set_viewport, dispatch_event`). Please publish the **authoritative** verb list + per-verb field schema — ideally as a real discriminated-union schema for a step, or at minimum a documented table at `/health/capabilities` or `/admin/capabilities` (those endpoints exist but their response schemas are empty `{}`).

### 3.4 CORS — required for browser clients

Our app runs in a browser at `https://dev.vault.sgraph.ai` and calls your service cross-origin. **Some server instances return no CORS headers**, so the browser blocks every readable response (`Failed to fetch`) — including `GET /openapi.json` and `GET /health/status`. Other instances work. Please make CORS **consistent across all deployed images**:

- `Access-Control-Allow-Origin`: the vault origin(s) (e.g. `https://dev.vault.sgraph.ai`), or a configured allow-list.
- `Access-Control-Allow-Headers`: must include `x-sgraph-access-token` and `content-type`.
- `Access-Control-Allow-Methods`: `GET, POST, OPTIONS`.
- Answer the `OPTIONS` preflight with 204.

Without this, the tool literally cannot talk to the affected servers from the browser.

### 3.5 TLS / cert

Instances serve self-signed certs on raw IPs, so browsers and tooling need to bypass verification. Not blocking for us, but a note: a stable hostname with a real cert per ephemeral instance (or a documented CA) would remove a class of "can't connect" confusion. At minimum, document that self-signed is expected.

### 3.6 Health endpoint surface

There are three overlapping health groups (`/info/*`, `/admin/*`, `/health/*`) and their OpenAPI response schemas are all empty `{}`. Please (a) document what each returns, and (b) expose a lightweight **`GET /health/status`** that's cheap, tokenless if possible, and returns `{ version, status, browser_pool, uptime_ms }` so our Targets "Test" button has a fast, reliable check.

---

## 4. The artefact contract we need (screenshots, video, etc.)

Once §2 is fixed, artefacts become central. We render them inline in the browser, so the **shape matters**. Please make each artefact a self-describing object:

```json
{
  "type": "screenshot",            // screenshot | video | pdf | har | trace | console_log | network_log | page_content
  "step_index": 1,                  // which step produced it (null for sequence-level)
  "sink": "inline",                 // inline | vault | s3 | local_file
  "content_type": "image/png",      // MIME — lets the client decide how to render
  "encoding": "base64",             // base64 | utf8 | url
  "data": "iVBORw0KGgo...",         // when sink=inline: the bytes; otherwise omit
  "ref": { "vault_key": "...", "path": "...", "version": "..." },  // when sink=vault
  "url": "https://...",             // when sink=s3/local_file and a URL is available
  "size_bytes": 48213,
  "filename": "step-1.png"
}
```

### 4.1 Capture semantics — does `capture_config` imply a terminal screenshot, or only route explicit steps? (please clarify + ideally implement implicit capture)

This is the most important **semantic** question, separate from the §2 crash. Consider:

```json
{ "steps": [ { "action": "navigate", "url": "https://example.com", "wait_until": "load" } ],
  "capture_config": { "screenshot": { "enabled": true, "sink": "inline" } } }
```

There is **no `screenshot` step**, but the caller has set `capture_config.screenshot.enabled = true`. The intuitive expectation is that the service returns **a screenshot of the final browser state** (how the page was left at the end of the sequence). It is surprising and easy to get wrong if this returns no artefact.

Three possible models — please pick one, **document it**, and ideally implement (1) or (3):

1. **Config-driven (expected):** `capture_config.screenshot.enabled` ⇒ always capture a **terminal** screenshot of the final page at sequence end, no step required. The `screenshot` *step* is only for **mid-sequence** captures.
2. **Step-driven (today's apparent behaviour):** `capture_config` only routes/encodes artefacts that explicit steps produce; no `screenshot` step ⇒ no screenshot. (This is the footgun.)
3. **Hybrid (best):** explicit `screenshot` steps capture at those points **and** `enabled` adds an automatic terminal capture. Per-step and terminal artefacts are distinguishable via `step_index` (terminal = `null`).

Strong supporting hint from your own schema: `capture_config` already has a **`screenshot_on_fail`** toggle that is sequence-level and step-independent. If the service can screenshot "on fail" without a step, it can screenshot "at end" without a step — so implicit terminal capture is consistent with the existing design. We'd suggest: `screenshot.enabled` → terminal screenshot on success; `screenshot_on_fail.enabled` → terminal screenshot when the sequence ends in failure; explicit `screenshot` steps → mid-run captures. The same logic should extend to `page_content` (return the final DOM) and `har`/`console_log`/`network_log` (cover the whole sequence, not a single step).

**Verification:** the example above must return one artefact with `type: "screenshot"`, `step_index: null` (terminal), and decodable inline PNG bytes.

Specific asks:
- **`inline` sink must return the actual bytes** (base64) with a correct `content_type`. Today even with `capture_config.screenshot.enabled=true, sink=inline` we get `artefacts: []` — partly the §2 crash, but also possibly the step-vs-config semantics above; please confirm inline base64 delivery works post-fix **for both** an explicit screenshot step and a config-only terminal capture.
- For **`sink: "vault"`**, return the `Schema__Vault_Ref__BaseModel` you wrote it to, so we can fetch/display it from the vault. (Great fit for our tool — runs already persist to the vault.)
- Keep large artefacts **out of the JSON by default**: a sensible default is `screenshot=inline`, but `video/har/trace=vault-or-s3` since they're big. Document the size cap on `inline`.
- For `format: "html"` screenshots and `page_content`, return as `content_type: text/html`, `encoding: utf8`.

---

## 5. Examples — the sequences we want to run

These are representative of what users will build. They should all return 200 with per-step results and (where requested) artefacts.

### 5.1 Smoke: open + screenshot (the simplest useful test)
```json
{ "steps": [
    { "action": "navigate", "url": "https://example.com" },
    { "action": "screenshot", "full_page": true }
  ],
  "capture_config": { "screenshot": { "enabled": true, "sink": "inline" } } }
```

### 5.2 Wait + verify (title/selector)
```json
{ "steps": [
    { "action": "navigate", "url": "https://sgraph.ai", "wait_until": "load" },
    { "action": "wait_for", "selector": "main", "timeout": 8000 },
    { "action": "screenshot", "full_page": false },
    { "action": "evaluate", "expression": "document.title" },
    { "action": "get_url" }
  ],
  "capture_config": { "screenshot": { "enabled": true, "sink": "inline" } } }
```

### 5.3 Form interaction (type, submit, wait, capture)
```json
{ "steps": [
    { "action": "navigate", "url": "https://duckduckgo.com" },
    { "action": "fill", "selector": "input[name=q]", "value": "playwright automation" },
    { "action": "press", "key": "Enter" },
    { "action": "wait_for", "selector": "#links", "timeout": 10000 },
    { "action": "screenshot", "full_page": false },
    { "action": "get_url" }
  ] }
```

### 5.4 Multi-page journey with capture-everything (the stress case)
```json
{ "steps": [
    { "action": "navigate", "url": "https://sgraph.ai", "wait_until": "networkidle" },
    { "action": "wait_for", "selector": "main", "timeout": 8000 },
    { "action": "screenshot", "full_page": false },
    { "action": "click", "selector": "a:has-text('About')" },
    { "action": "wait_for", "selector": "h1", "timeout": 8000 },
    { "action": "get_content" },
    { "action": "screenshot", "full_page": true },
    { "action": "evaluate", "expression": "document.querySelector('h1')?.innerText" },
    { "action": "get_url" }
  ],
  "capture_config": {
    "screenshot": { "enabled": true, "sink": "inline" },
    "har":        { "enabled": true, "sink": "vault" },
    "console_log":{ "enabled": true, "sink": "inline" },
    "include_performance_data": true
  },
  "sequence_config": { "halt_on_error": false, "default_step_timeout_ms": 15000 } }
```

If 5.4 returns 200 with per-step results, an inline screenshot on each screenshot step, a HAR ref, and console output, the service is in good shape for what we're building.

---

## 6. How to validate the whole thing as workflows get more complex

A regression checklist the maintainer can run after any change to the image:

1. **Per-verb smoke.** One sequence per verb (navigate, click, fill, press, select, hover, scroll, wait_for, screenshot, evaluate, get_content, get_url, set_viewport, dispatch_event) against `https://example.com` / a known fixture — each returns 200 and `status: passed`.
2. **Artefact round-trip.** §5.1 returns a decodable PNG inline; decode and assert it's a valid image (non-zero dimensions).
3. **Failure isolation.** A sequence with a deliberately bad selector (`wait_for #nope`) returns **200**, that step `failed` with an `error_message`, and — with `halt_on_error:false` — later steps still run.
4. **Halt semantics.** Same bad step with `halt_on_error:true` marks subsequent steps `skipped`.
5. **Timeout behaviour.** A `wait_for` on a never-appearing selector respects `timeout`/`default_step_timeout_ms` and reports a timeout error, not a hang.
6. **Concurrency.** Fire ~10 sequences in parallel; assert no cross-talk (each gets its own browser context), no event-loop errors, stable `trace_id`s. (This is exactly where the sync/async bug bites hardest.)
7. **Big-page resilience.** Full-page screenshot of a long page; large `get_content`; assert sane payload sizes and that inline caps kick in.
8. **CORS preflight.** `OPTIONS /sequence/execute` from the vault origin returns 204 with the right headers; a browser `fetch` from `https://dev.vault.sgraph.ai` succeeds.
9. **Spec accuracy.** `GET /openapi.json` reflects reality: typed 200 response, documented step verbs, documented capture_config.
10. **Health.** `GET /health/status` is fast and returns version + status.

Publishing these as a CI suite in the image repo would let us trust new versions on sight.

---

## 7. New capabilities that would help (ranked)

Now is the moment to ask — here's what would materially expand what our tool can do:

1. **Live capability/verb introspection.** A real `GET /health/capabilities` (or `/admin/capabilities`) returning the verb list, each verb's JSON-schema for its fields, supported `wait_until` states, screenshot formats, and capture sinks. We already have a "Live capabilities" panel ready to render this — today it can only show raw paths because the schemas are empty.

2. **Assertion / expectation steps.** First-class steps like `expect_selector_visible`, `expect_title_contains`, `expect_url_matches`, `expect_text`, `expect_status` that the service evaluates and reports pass/fail. We currently fake assertions client-side by injecting `evaluate`/`get_url` steps and checking the result; native assertions would be far more robust and is the natural home for a QA tool.

3. **Keep the service fully stateless — and enforce it.** This is a design principle we want reinforced, not a feature request. **Every request must be self-contained, and no state may persist between requests.** Concretely:
   - Each `/sequence/execute` (and each one-shot) gets a **fresh browser context** and is torn down at the end — no shared cookies, storage, cache, or logged-in session leaking from one request into the next.
   - **No credentials are retained server-side.** Any cookies, storage-state, tokens, or `extra_http_headers` passed in a request are used for that request only and then discarded — never written to disk beyond the request's lifetime, never reused for a later request.
   - **No temp files survive the request.** Screenshots, videos, traces, HARs, downloads, user-data-dirs, and any scratch files must be cleaned up when the request completes (success or failure). On an ephemeral EC2 box this also protects against disk fill-up over a long-lived instance.
   - Statelessness is what makes the service safe to point at arbitrary targets and safe to run many sequences concurrently. Please audit that nothing (browser profile dirs, `/tmp` artefacts, in-memory session caches) outlives a single request, and consider a periodic sweep as a backstop.

   (If authenticated flows are ever needed, the caller should supply credentials **in each request** via the existing `credentials` field — the service should not hold them.)

4. **`evaluate` allow-list, documented.** `evaluate` is powerful but presumably sandboxed. Document what's permitted (read-only expressions? which globals?) and return a clear error when an expression is rejected, so users know the boundary.

5. **Network/route control.** Optional per-sequence request interception: block resource types (images/fonts) for speed, stub responses, or assert that a given request fired. Huge for deterministic tests.

6. **Per-step waits and retries.** Optional `retry: { count, delay_ms }` and richer `wait_for` (text, network-idle, function) so flaky pages don't fail the suite.

7. **Trace/video as first-class debugging artefacts.** With the artefact contract in §4, a Playwright **trace** (`trace.zip`) per failed run, stored to the vault, would let us add a "download trace" button — gold for debugging complex failures.

8. **Idempotent `sequence_id` / dedupe.** Let the client pass a `sequence_id` and have the service treat re-submission idempotently (return the prior result), so retries don't double-run.

9. **Structured timing per step.** You already return great top-level `timings`; per-step `timings` (navigation vs script vs wait) would power a performance view.

10. **Live result streaming for long sequences.** For long suites, an option to stream step results (SSE/chunked) so the UI shows progress live instead of waiting for the whole sequence.

11. **Live browser video streaming (not just recorded video) — high interest.** Our main deployment is the ephemeral EC2 instance, and we'd like to *watch the browser live* while a sequence runs, not only download a recording afterward. Worth exploring:
    - A streamable feed of the running Chromium/Chrome page — e.g. an MJPEG/WebRTC stream, or CDP `Page.startScreencast` frames relayed over a websocket — that the client can render in a `<video>`/`<canvas>` for the duration of a run.
    - This is a live view of the same temporary browser process the sequence drives, exposed only while that request/session is active.

12. **Time-boxed remote control of the browser (share the CDP websocket) — high interest.** Beyond watching, we'd like to *take control* of the live browser for a limited window — for interactive debugging, manual login, or exploratory steps mid-run. Concretely:
    - Expose the running browser's **Chrome DevTools Protocol (CDP) websocket endpoint** (the `webSocketDebuggerUrl` from `--remote-debugging-port`) through a **short-lived, token-scoped proxy** so a client can attach Playwright/puppeteer/`chrome-remote-interface` to that exact instance and drive it remotely.
    - Must be **time-limited** (auto-expire after N minutes / on sequence end), **scoped to that one ephemeral browser process**, and revocable. When the lease ends, the browser process and all its temp state are torn down per §7.3 (statelessness).
    - On Linux this is the headless Chromium/Chrome process the service already launches; the ask is to make its debugging socket reachable for a bounded period rather than keeping it private to the service.

> **Note for the implementing agent:** feel free to **experiment with new endpoints and expand the exposed methods**. These run on an **ephemeral EC2 instance behind an API key**, so the security blast radius of adding capabilities (live screencast, CDP relay, richer step verbs, debug routes) is low. Prototype freely; we'll adapt the client to whatever you expose (the "Live capabilities" panel in §7.1 is designed to discover new methods automatically once the spec advertises them). The hard constraints are §2 (correctness) and §7.3 (statelessness — anything added must still leave no state between requests).

---

## 8. Summary of asks

| # | Ask | Priority |
|---|---|---|
| §2 | Fix sync-Playwright-in-asyncio crash (screenshot & all artefact steps) | **Blocking** |
| §2.1 | Ship a **side-by-side async** `/sequence/execute-async` (same contract) to compare vs sync and as a fallback | High |
| §3.1 | Per-step error isolation; never 400 the whole sequence for a step failure | High |
| §3.4 | Consistent CORS across all images (incl. `x-sgraph-access-token`, OPTIONS) | High |
| §4 | Self-describing artefact objects; inline base64 actually delivered | High |
| §4.1 | Clarify + implement capture semantics: `capture_config` should yield a **terminal** screenshot with no explicit step | High |
| §3.2/3.3 | Type the 200 response + publish step-verb schema in OpenAPI | Medium |
| §3.6 | Fast, documented `/health/status` | Medium |
| §7.1 | Live capability introspection endpoint with real schemas | Medium |
| §7.2 | Native assertion steps | Medium |
| §7.3 | **Enforce statelessness** — no state, credentials, or temp files between requests | High |
| §7.11/7.12 | **Live browser video streaming + time-boxed remote CDP control** (EC2 use case) | Explore |
| §7.4–10 | Network control, retries, trace artefacts, idempotency, result streaming | Nice-to-have |

The one thing that unblocks everything else is **§2**. Once screenshots come back, the tool becomes genuinely useful, and the rest is about scaling to complex, trustworthy workflows.
