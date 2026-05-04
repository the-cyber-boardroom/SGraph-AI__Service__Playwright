# QA Findings — Playwright Service Proxy Support

**Date:** 17 April 2026
**Target service:** `https://dev.playwright.sgraph.ai` (AWS Lambda, `sg-playwright` v0.38.0, Playwright 1.58.0)
**Browser target:** `https://send.sgraph.ai/en-gb/`
**Session type:** Claude QA session with dev-pack clone + service API key

---

## Executive Summary

The Playwright service works end-to-end for **non-proxied** sessions (9/9 tests passed in the baseline suite). The **proxied** session path has one primary functional bug and three secondary issues worth filing.

| Area | Status |
|---|---|
| Baseline suite (health, session lifecycle, navigate, screenshot, get-content, get-url, close) | ✅ 9/9 passing |
| Proxy config accepted by the API | ✅ Schema validates, session creates |
| Proxy actually used for HTTPS navigation | ❌ Every navigation hangs → CloudFront 504 |
| Session cleanup on client timeout | ⚠ Leaks warm Chromium in Lambda |

**Headline finding:** authenticated proxies cannot be used through the service today. `chromium.launch(proxy={"username", "password"})` does not work reliably for the modern Playwright headless shell — auth needs to be handled via the **CDP Fetch domain**, registered post-context per page. A working reference implementation exists at `sg_send_qa.browser.Proxy_Via_Browser` in the SG_Send__QA repo. The fix is a schema change plus a new session-init code path (details in Bug #1).

---

## Baseline Suite Results

Ran the canonical session lifecycle from the briefing. All 9 tests passed.

| # | Endpoint | Time | Notes |
|---|---|---|---|
| 1 | `GET /health/info` | ~900 ms | `service=sg-playwright pw=1.58.0 target=lambda` |
| 2 | `GET /health/status` | ~400 ms | |
| 3 | `GET /health/capabilities` | ~420 ms | See [capabilities table](#capabilities-snapshot) |
| 4 | `POST /session/create` | ~835 ms | Chromium cold start inside Lambda — quicker than the 5–15 s the briefing anticipates |
| 5 | `POST /browser/navigate` | ~3.7 s | `send.sgraph.ai/en-gb/` |
| 6 | `POST /browser/screenshot` | ~1.1 s | 53 KB PNG |
| 7 | `POST /browser/get-content` | ~440 ms | 827 chars — Beta Access gate rendered |
| 8 | `POST /browser/get-url` | ~200 ms | |
| 9 | `DELETE /session/close/{id}` | ~840 ms | Total session duration 5.8 s |

The rendered page confirmed a successful real-world navigation: the Beta Access gate, "Your files, your keys, your privacy" tagline, and the test-files panel (text, json, html, png, pdf, md) were all present in both the screenshot and the extracted text.

### Capabilities snapshot

```json
{
  "max_session_lifetime_ms": 900000,
  "supports_persistent": false,
  "supports_video": true,
  "available_browsers": ["chromium"],
  "supported_sinks": ["vault", "inline", "s3"],
  "memory_budget_mb": 5120,
  "has_vault_access": false,
  "has_s3_access": true,
  "has_network_egress": true,
  "proxy_configured": false
}
```

Note: `supported_sinks` advertises `vault` but `has_vault_access: false` — the vault sink would fail at runtime. Worth reconciling either the advertised list or the access flag.

---

## Proxy Testing — What Was Attempted

Configured a TLS-intercepting proxy via the `Schema__Proxy__Config` shape documented in `schema-catalogue-v2.md` §11.2:

```json
{
  "browser_config": {
    "browser_name": "chromium",
    "headless": true,
    "proxy": {
      "server": "http://<redacted host>:<port>",
      "username": "<redacted>",
      "password": "<redacted>",
      "bypass": [],
      "ignore_https_errors": true
    }
  },
  "capture_config": {
    "screenshot": {"enabled": true, "sink": "inline"},
    "include_execution_result": true
  }
}
```

Test targets: `https://api.ipify.org/?format=json` (to verify egress IP change), `https://example.com/`, `https://send.sgraph.ai/en-gb/`.

---

## Findings

### 🐛 Bug #1 — Proxy authentication not wired up (P1)

**Symptom:** Every HTTPS navigation through a proxied session hangs. Chromium reports:

```
Page.goto: Timeout 8000ms exceeded.
  - navigating to "https://api.ipify.org/?format=json", waiting until "load"
```

With no step-level timeout, the hang propagates all the way to CloudFront's 30 s gateway timeout, returning a 504 to the client:

```
504 Gateway Timeout
The request could not be satisfied.
```

**Diagnosis:**

1. **The proxy is reachable from the Lambda.** Evidence: navigating to the proxy URL as a *regular target* (i.e. `http://<proxy-host>:<port>/` as a plain navigation, with no `proxy` config on the session) returned **`net::ERR_UNEXPECTED_PROXY_AUTH` in 0.6 s**. This is the browser refusing to render an HTTP 407 response from the proxy. Network path: fine. Proxy: alive. TLS: not an issue at this layer.

2. **The proxy is demanding authentication (HTTP 407 on CONNECT)** and Chromium isn't producing credentials. The hang is consistent with Chromium receiving a 407 over the CONNECT tunnel, having no way to answer, and holding the socket open until Lambda times out.

3. **The obvious fix — passing `username`/`password` to `chromium.launch(proxy={...})` — is not reliable.** Playwright documents those kwargs but they only work for a subset of Chromium launch paths and do not work consistently with the modern headless shell. Confirmed against a working reference implementation (see below): **authenticated proxies require the CDP Fetch domain**, not launch-level kwargs.

**Root cause & correct fix:**

The service currently maps `Schema__Proxy__Config` fields straight to the `chromium.launch(proxy=...)` kwarg. That's not enough for any proxy that requires auth. The working pattern is:

```python
# After context/page creation, open a CDP session and register two Fetch handlers:
cdp = page.context.new_cdp_session(page)
cdp.send("Fetch.enable", {"handleAuthRequests": True})

# Handler 1: synthesise Proxy-Authorization on 407 challenges
cdp.on("Fetch.authRequired", lambda params: cdp.send("Fetch.continueWithAuth", {
    "requestId": params["requestId"],
    "authChallengeResponse": {
        "response": "ProvideCredentials",
        "username": username,
        "password": password,
    },
}))

# Handler 2: pass every other request through untouched
#   REQUIRED — enabling Fetch with handleAuthRequests pauses ALL requests,
#   not just auth-challenged ones. Without this, every page hangs.
cdp.on("Fetch.requestPaused", lambda params: cdp.send(
    "Fetch.continueRequest", {"requestId": params["requestId"]}))
```

Both handlers should swallow "stale request id" exceptions — CDP events can fire after a navigation has abandoned a request, and those calls throw benign errors that mean nothing actionable.

**Where this lives in the service architecture:**

- **Launch time** — still pass `server`, `bypass`, and `ignore_https_errors` to `chromium.launch(proxy=...)`. These work correctly.
- **Post-context, per-page** — open a CDP session against each page and register the two Fetch handlers above. This must happen *before* the first navigation.

This is a behavioural change: sessions with proxy auth will need the CDP handlers attached as part of session/page initialisation, not at launch.

**Recommended schema (breaking change — acceptable given no legacy callers):**

The current flat `Schema__Proxy__Config` conflates server-level and auth-level concerns and misleadingly suggests `username`/`password` are launch kwargs. Suggested redesign:

```python
class Schema__Proxy__Auth__Basic(Type_Safe):                # Basic auth via CDP Fetch
    username : Safe_Str__Username
    password : Safe_Str                                     # never logged

# Extensible — additional auth types can be added without breaking callers:
# class Schema__Proxy__Auth__Bearer(Type_Safe): token: Safe_Str
# class Schema__Proxy__Auth__NTLM(Type_Safe):   ...

class Schema__Proxy__Config(Type_Safe):
    server              : Safe_Str__Url                            # http://proxy.host:port
    bypass              : List[Safe_Str__Host]                     # passthrough hosts
    ignore_https_errors : bool                         = False     # TLS-intercepting proxies
    auth                : Schema__Proxy__Auth__Basic   = None      # None = open proxy, no auth
```

Why this shape:

- Flat `username`/`password` at the top level is a **trap** — it implies they map to `chromium.launch(proxy={"username": ...})`, which is the exact misconception that caused this bug. Nesting them inside `auth` signals they go through a different mechanism.
- `auth: None` cleanly expresses "open proxy" with no special case.
- Adding `Bearer` / `NTLM` / other auth types later is purely additive — existing callers don't break.
- The type name `Schema__Proxy__Auth__Basic` is self-documenting about what's supported today.

**Reference implementation:** A working CDP-based proxy-auth wrapper exists at `sg_send_qa.browser.Proxy_Via_Browser` (in the `SG_Send__QA` repo). That class demonstrates:

- CDP Fetch auth handler registration
- Stale-request-id error swallowing
- Paired `requestPaused` handler to avoid pausing all traffic
- Cookie injection for mitmproxy-style request tagging

It's directly adaptable into the service's session/page initialisation path.

**Supplementary: the `Safe_Str__Url` regex also rejects `user:pass@host` authority form.** While not the fix (inline credentials were never the right answer), the regex should stay as-is — nesting auth under `Schema__Proxy__Auth__Basic` removes any reason for callers to need that URL form.

**Repro steps:**

1. Ensure Lambda is warm (one no-proxy session first).
2. `POST /session/create` with a `proxy.server` pointing at *any* proxy that requires auth, and valid `proxy.username` / `proxy.password` fields.
3. `POST /browser/navigate` to any HTTPS URL.
4. Observe: HTTP 504 after ~30 s (or `status: failed, error_message: "Page.goto: Timeout..."` if `step.timeout_ms` is set short).

---

### 🔸 Observation #2 — `Safe_Str__Url` regex excludes proxy-auth URL form (downgraded from P2 to cosmetic)

**Symptom:** `proxy.server = "http://user:pass@host:port"` → 500 Internal Server Error, schema validation failure because `Safe_Str__Url`'s regex forbids the `user:pass@` authority form.

**Status:** This was originally filed as a P2 blocker because it removed the only client-side workaround for Bug #1. With Bug #1's proper fix (CDP-based auth + nested `Schema__Proxy__Auth__Basic`), callers never need to put credentials in the server URL. The regex should stay as-is — it's protecting other fields legitimately.

**Action:** No change needed to `Safe_Str__Url`. Documentation should explicitly state that proxy credentials go in the `auth` field, not the `server` URL.

---

### 🐛 Bug #3 — Sessions leak when CloudFront times out mid-action (P3)

**Symptom:** When `POST /browser/navigate` hangs inside the Lambda and CloudFront returns a 504 at 30 s, the session itself is not torn down. It remains in `status: active` in `/session/list`, with the Chromium process still running inside the Lambda.

**Evidence:** After a proxied-navigate-that-504'd, `GET /session/list` returned:
```json
[{"session_id":"safe-id_qmxts","status":"active","total_actions":2, ...}]
```
`DELETE /session/close/{id}` successfully cleaned it up when called explicitly.

**Impact:**
- Chromium processes accumulate on warm Lambda containers until the 900 s max session lifetime expires.
- Clients have no way of knowing whether the 504 means "navigate failed" or "navigate is still running on the server" — so robust clients need to defensively call `/session/close` on every 504.

**Recommendation:**
- **Short-term:** Default `Page.goto` timeout inside the service should be < CloudFront's gateway timeout (e.g. 25 s), so the service returns a real `status: failed` before the infrastructure gives up.
- **Longer-term:** Any navigation/action handler that catches a timeout should optionally tear down the session or at least mark it `status: degraded`.

---

### 🐛 Bug #4 — Lambda state poisoned after leaked proxied session (P4)

**Symptom:** While a leaked proxied session was still active, **every subsequent `POST /session/create` call** (including no-proxy ones) returned:

```
HTTP 400
{"detail": "Error: It looks like you are using Playwright Sync API inside the asyncio loop.
            Please use the Async API instead."}
```

5/5 attempts failed with this error, deterministically. Cleaning up the leaked session (via `DELETE /session/close/{id}`) immediately restored normal operation — the very next `session/create` returned 200.

**Diagnosis:** This is a classic Playwright footgun — using the sync API from within an asyncio event loop raises this exact exception. Two code paths appear to share a Playwright context/client:

- The primary request path uses the async API correctly.
- The proxy-configured creation path (or a cleanup path triggered by the leaked session) uses the sync API, which raises this error when invoked from FastAPI's event loop.

**Likely causes (speculation — worth confirming against the source):**
- A singleton `sync_playwright()` is being constructed for proxy-aware launches rather than `async_playwright()`.
- Or a cleanup / health-check code path runs sync Playwright calls and only triggers when there are active sessions.

**Recommendation:** Audit the service for `sync_playwright` usage. All Playwright calls from inside FastAPI handlers should be async. If a sync path is genuinely needed, it must run in a worker thread (`asyncio.to_thread(...)`).

---

### 🔸 Observation #5 — Capabilities endpoint doesn't surface per-session proxy support (P5, cosmetic)

`capabilities.proxy_configured: false` reflects whether a **default** proxy is set via `ENV_VAR__DEFAULT_PROXY_URL` (correct per `routes-catalogue-v2.md` line 907). It doesn't tell the caller whether per-session `browser_config.proxy` is supported at all.

**Recommendation:** Once Bug #1 is fixed, add a distinct capability flag:

```json
{
  "proxy_configured": false,            // default proxy configured service-side
  "supports_per_session_proxy": true    // can accept proxy in browser_config
}
```

---

## Secondary Observations (not bugs, but worth documenting)

### Nav step status vocabulary

The briefing's sample code (line 75) prints `nav_result['step_result']['status']`. The actual value returned is **`"passed"`** — not `"ok"` or `"success"` as one might expect from the briefing phrasing. Any assertion logic copying the briefing pattern should accept `"passed"`.

### Briefing doesn't mention API key requirement

The dev-pack briefing `briefing__continue-qa-testing.md` walks through the API end-to-end without mentioning that **every endpoint except `/docs`, `/openapi.json`, and `/auth/set-cookie-form` requires a client API key header**. A new session starting from the briefing alone will hit a 401 wall on step 1. The header/cookie name (`api-key__for__SGraph-AI__App__Send`) is discoverable from the public `/auth/set-cookie-form` HTML, but the value must be supplied out-of-band.

**Recommendation:** Add an "Authentication" section to the briefing before "How to Call the API", documenting the header name and pointing at the secrets source (`FAST_API__AUTH__API_KEY__VALUE`).

### CloudFront 504 shape

When CloudFront returns a 504, the body is an HTML page from CloudFront, not a JSON error from the service:

```html
<!DOCTYPE HTML ...>
<TITLE>ERROR: The request could not be satisfied</TITLE>
<H1>504 Gateway Timeout ERROR</H1>
...
```

Any client parsing `response.json()` on error paths will crash. Clients must check `Content-Type` or `response.status_code` first.

---

## Suggested Fix Priority

| Priority | Issue | Why |
|---|---|---|
| **P1** | #1 — Proxy auth needs CDP Fetch handlers (not launch kwargs) | Blocks all authenticated-proxy operation; requires schema change + new session-init code path |
| **P1** | #4 — Async/sync Playwright mix-up | Service-wide 400s when a proxied session leaks — bad blast radius |
| **P2** | #3 — Session leak on CloudFront 504 | Resource leak in warm Lambdas, unclear client contract |
| **P3** | #5 — Capabilities flag | Discoverability improvement, cosmetic |
| **Cosmetic** | #2 — `Safe_Str__Url` regex | No longer a blocker once #1's schema is adopted — `auth` field replaces any need for inline creds |

Fixing #1 likely makes #4 less visible (fewer proxied sessions leak if proxied navigation works), but #4 is a real sync/async bug that should be fixed independently.

### Implementation checklist for #1

For the service team, concrete steps:

1. **Refactor `Schema__Proxy__Config`** — flatten auth into a nested `Schema__Proxy__Auth__Basic` (design in the Bug #1 section). No backwards-compat needed.
2. **At session init**, split proxy config:
   - `server`, `bypass`, `ignore_https_errors` → passed to `chromium.launch(proxy=...)` as today.
   - `auth` (if present) → register CDP Fetch handlers against each new page.
3. **Reference the working implementation** at `sg_send_qa.browser.Proxy_Via_Browser` in the SG_Send__QA repo — it has the correct CDP handler wiring, stale-request-id handling, and the critical `Fetch.requestPaused` passthrough.
4. **Add integration test** against a test mitmproxy (can be stood up in CI with Docker) — should prove navigation-through-auth'd-proxy works end-to-end and that egress IP changes.
5. **Update `capabilities` endpoint** (see #5) to advertise `supports_per_session_proxy` and the supported auth mechanisms.

---

## Test Artefacts

| File | Purpose |
|---|---|
| `qa_playwright_service.py` | Reusable baseline suite (9 tests, runs in ~9 s) |
| `qa_proxy_test.py` | Proxy-specific harness — drop-in once proxy is fixed |
| `send_landing.png` | Baseline screenshot of `send.sgraph.ai/en-gb/` (proxy-less path working) |
| `send_landing.txt` | Extracted text — Beta Access gate content |
| `capabilities.json` | Capability snapshot at test time |

The proxy harness is structured to prove two things once the fix lands:
1. Navigation succeeds through the proxy (end-to-end render of `send.sgraph.ai`).
2. Egress IP has changed — a direct `api.ipify.org` probe vs a proxied one should return different IPs, confirming traffic is actually going through the proxy rather than the Lambda's native egress (`16.60.168.73` in the `eu-west-2` range during these tests).

---

## Next Steps When Re-testing

1. Apply P1 fix (propagate `username`/`password` to `chromium.launch`).
2. Re-run `qa_proxy_test.py` — should complete both probes and produce `send_via_proxy.png`.
3. Verify the direct egress IP differs from the proxied egress IP.
4. Rerun baseline suite to confirm no regression.
5. File the remaining P2/P3/P4/P5 items as separate issues — they're independent of P1.
