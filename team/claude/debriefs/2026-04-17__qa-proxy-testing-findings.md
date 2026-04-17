# Debrief — QA session — authenticated-proxy testing against dev Lambda

- **Date:** 2026-04-17
- **Commit(s):** `deb5c79` (added QA doc to the human inbox). No production code changes originated from this session — findings only.
- **Role:** QA (separate Claude session, dev-pack clone + service API key; not the Dev session that shipped v0.1.13).
- **Scope:** Black-box testing of `https://dev.playwright.sgraph.ai` (v0.38.0 image / spec tag, Playwright 1.58.0). Baseline session lifecycle + authenticated-proxy paths.
- **Artefact:** [`team/humans/dinis_cruz/briefs/04/17/qa-findings__proxy-testing.md`](../../humans/dinis_cruz/briefs/04/17/qa-findings__proxy-testing.md).
- **Status:** Report accepted. Triage complete — P1 bugs #1 and #4 are now on the Dev roadmap.

## What the QA session delivered

### Baseline suite — proved the non-proxied happy path

9/9 tests passed against the live Lambda:

| Endpoint             | Wall-clock | Notes |
|----------------------|------------|-------|
| `GET  /health/info`  | ~900 ms    | service=sg-playwright, pw=1.58.0, target=lambda |
| `POST /session/create` | ~835 ms  | Cold Chromium faster than the briefing's 5–15 s estimate |
| `POST /browser/navigate` → `send.sgraph.ai/en-gb/` | ~3.7 s | Real render confirmed |
| `POST /browser/screenshot` | ~1.1 s | 53 KB PNG |
| `POST /browser/get-content` | ~440 ms | 827 chars, Beta Access gate rendered |
| Total session wall clock | 5.8 s  | 9 calls, end-to-end |

The screenshot and extracted text corroborated that navigation hit the real origin (Beta Access gate + test-files panel), not a cached or fallback page.

### Four engineering findings, ranked by blast radius

1. **P1 — Bug #1 — authenticated proxies unusable.** `chromium.launch(proxy={"username","password"})` does not work reliably on the modern headless shell; the tunnel stalls on 407. Fix requires the **CDP Fetch domain** (`handleAuthRequests=True` + paired `Fetch.authRequired` / `Fetch.requestPaused` handlers), registered per-page post-context. Reference implementation pointed to `sg_send_qa.browser.Proxy_Via_Browser` in the `SG_Send__QA` repo — saves the Dev team a half-day of CDP spelunking.

2. **P1 — Bug #4 — Lambda state poisoned across requests.** After a proxied session leaked, every subsequent `/session/create` returned `HTTP 400 "sync Playwright API inside asyncio loop"`. 5/5 deterministic. Cleaning the leaked session via `DELETE /session/close/{id}` immediately restored health. Diagnosed as a sync-vs-async Playwright mix-up, with speculation that a singleton sync_playwright was being re-used across requests.

3. **P3 — Bug #3 — session leak on CloudFront 504.** When a navigation stalls and CF times out at 30 s, the service never tears the session down. Chromium accumulates on warm Lambdas until the 900 s lifetime ceiling; clients can't distinguish "navigate failed" from "navigate still running". Recommendation: per-action timeout < 30 s so the service fails fast before CloudFront.

4. **P3 — Observation #5** — `capabilities.proxy_configured` only reflects the *default* proxy env-var, not per-session proxy support. Needs a second flag (`supports_per_session_proxy`) once Bug #1 is fixed.

Plus three non-bug observations: `Safe_Str__Url` regex blocks `user:pass@host` (downgraded to cosmetic once the schema change lands), briefing doesn't mention the API-key requirement, CloudFront 504s return HTML not JSON so clients must check `Content-Type`.

### Schema redesign proposal (adopted by Dev)

The QA session proposed flattening `Schema__Proxy__Config` into a nested shape:

```python
class Schema__Proxy__Auth__Basic(Type_Safe):
    username : Safe_Str__Username
    password : Safe_Str                       # never logged

class Schema__Proxy__Config(Type_Safe):
    server              : Safe_Str__Url
    bypass              : List[Safe_Str__Host]
    ignore_https_errors : bool                       = False
    auth                : Schema__Proxy__Auth__Basic = None    # None = open proxy
```

The reasoning captured in the brief — *flat `username`/`password` at the top level is a trap because it implies they map to launch kwargs* — is exactly right and motivates why the Dev fix is not just "wire the creds through" but a surface-level redesign. Breaking change is acceptable: no legacy callers.

## Failures & lessons (good-failure / bad-failure)

### Good failures (surfaced early, informed the Dev plan)

- **Bug #1's diagnosis cost almost nothing because the QA session owned both sides of the proxy.** Knowing `net::ERR_UNEXPECTED_PROXY_AUTH` fires in 0.6 s when the proxy is hit as a plain URL let QA *rule out* network/TLS/DNS before even looking at Chromium launch kwargs. That saved the Dev team from chasing the wrong layer first. The pattern — "navigate *to* the suspect endpoint as a regular target before diagnosing it as an intermediary" — belongs in the testing guide.
- **Bug #4 reproduced deterministically (5/5).** Deterministic reproduction on a live production Lambda is rare and valuable. It let Dev decide *before writing any code* that the fix had to include layered defences (watchdog for un-killable Lambdas), because the blast radius — every subsequent request 400s — is service-wide rather than per-session.
- **The schema-redesign proposal pre-empted a bad Dev instinct.** Without it, the obvious Dev fix would have been "pass `username`/`password` through to the CDP call and keep the flat schema". That would ship with the *same trap* the QA brief called out: a caller reading `server`, `username`, `password` at the top level of a config still assumes they go to `launch()`. Nesting under `auth` makes the different code path visually obvious.

### Bad failures (silent or recurring)

- **No integration test covered authenticated-proxy navigation before v0.38.0 shipped.** The service's test suite never exercised a proxy requiring auth, so Bug #1 only surfaced during manual QA against a live environment. The QA brief explicitly flags this as a gap (*"Add integration test against a test mitmproxy — can be stood up in CI with Docker"*). Without it, the exact same bug can re-land during any future refactor of the launcher. Follow-up is pending.
- **The briefing docs for new QA sessions omit the API-key requirement.** A new session starting from `briefing__continue-qa-testing.md` alone hits 401 on step 1 — the header name (`api-key__for__SGraph-AI__App__Send`) is only discoverable via the `/auth/set-cookie-form` HTML. The QA brief calls this out and recommends an Authentication section before "How to Call the API"; it has not yet been applied to the briefing.
- **`capabilities.supported_sinks` advertises `vault` but `has_vault_access: false`.** QA flagged the inconsistency. If a caller trusts the advertised list, the vault sink fails at runtime with a less-obvious error than a proper capability filter would give. Recon needed — either narrow the advertised list or make `has_vault_access` additive rather than a hard deny.
- **Client-side CloudFront 504 contract is undocumented.** A 504 returns HTML, not JSON — any client calling `response.json()` on error paths crashes. Callers have to defensively check `Content-Type`. Not the service's fault (it's CloudFront), but *is* the service's problem to document in the caller guide.

## Downstream effect on Dev (same session = v0.1.14-candidate)

The QA brief's P1-on-#1 + P1-on-#4 ranking drove this slice, committed as `216fa92` on `claude/general-session-HRsiq`:

- **L1 (already in v0.1.13)** — fresh `sync_playwright` per call. Almost certainly removes the root cause of Bug #4 on its own, but the QA session's "the Lambda is un-killable from outside" reframing was load-bearing for the next two layers.
- **L3 — Sequence__Runner wall-clock deadline** (`SG_PLAYWRIGHT__REQUEST_DEADLINE_MS`, default 25 s). Between steps the runner checks the deadline, marks remaining steps `SKIPPED`, and tears the session down. Can't interrupt a blocked `page.goto()`, but guarantees cleanup once the current step returns — addresses Bug #3 directly.
- **L6 — Request__Watchdog** (`SG_PLAYWRIGHT__WATCHDOG_MAX_REQUEST_MS`, default 28 s). Daemon thread + HTTP middleware. On breach it calls `os._exit(2)` — LWA sees the process die, AWS recycles the execution environment, the next invocation gets a fresh container. Works even when the main thread is fully deadlocked, because the watchdog runs on a separate OS thread and `os._exit` is a C-level syscall that bypasses Python cleanup.

Bug #1 (CDP Fetch proxy auth + `Schema__Proxy__Auth__Basic` refactor) is next on the queue. Bug #5 (capabilities flag) is deferred to the same slice since it's schema-adjacent.

## Follow-ups (Dev + Librarian + Architect)

- **Librarian:** link this debrief from the reality doc's "known issues" section when it next rolls forward. Add a cross-reference from `library/guides/testing_guidance.md` to the "QA owns the baseline suite + is the canonical source for live-Lambda findings" pattern.
- **Architect:** promote `Schema__Proxy__Auth__Basic` + the revised `Schema__Proxy__Config` into `library/docs/specs/schema-catalogue-v2.md` §11.2 once Dev lands the implementation. The shape is good; let's not let it stay only in a human-inbox brief.
- **Dev (open, this branch):** Bug #1 implementation + `capabilities.supports_per_session_proxy` flag. Slice aims at v0.1.15.
- **Dev (later):** integration test with a test mitmproxy in CI. Without it, Bug #1 will regress silently. Not blocking v0.1.15 but must not drift past v0.2.
- **Briefing owner:** Authentication section in `briefing__continue-qa-testing.md`. One-paragraph fix; has not happened.
- **Client docs:** "CloudFront 504 returns HTML, not JSON" note in the caller guide.

## Working pattern notes — QA session as a distinct role

This was the first formal QA debrief in the project. Two things that worked:

1. **QA was a separate session from Dev.** QA ran against a deployed Lambda with only the public API + briefing as inputs — no source-tree access biasing the test plan. That's why the findings read as *black-box symptoms + diagnosis* rather than *"here's what I know the code does wrong"*. Keep this separation.
2. **The brief named the likely root cause for each bug AND pointed at a reference fix.** For Bug #1 especially, the pointer to `sg_send_qa.browser.Proxy_Via_Browser` collapsed Dev's planning-to-implementation gap from hours to minutes. QA sessions that have access to sibling-repo reference implementations should always include the pointer rather than making Dev re-derive.
