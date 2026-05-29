---
title: "Playwright API — Guide for Agents (v0.2.42, PROPOSED target state)"
author: Architect (Claude, Opus 4.8)
date: 2026-05-29
status: PROPOSED — describes the API AFTER the planned work (dev-pack 01). NOT all of this exists yet; each section is tagged. Supersedes library/guides/v0.2.6__playwright-api-for-agents.md once built.
audience: the Playwright Workbench team (and any agent driving sg-playwright)
purpose: "Hand this back with: 'if we build this, does it do what you need?'"
---

# Playwright API — Guide for Agents (PROPOSED target state)

> **Read the tags.** Each capability is marked **[LIVE]** (works today), **[FIX]** (exists but
> being corrected), or **[NEW]** (proposed, not built yet). This lets you confirm the *target*
> contract before we build it. The canonical current-state guide remains
> `library/guides/v0.2.6__playwright-api-for-agents.md` until this ships.

## 0. Connection

```
BASE_URL = https://<vault-host>/pw          # same origin as the vault, via the reverse proxy
TOKEN    = <the vault access token>
```

- **Auth header is `x-sgraph-access-token`** — **not** `X-API-Key`. [LIVE] The `/pw` proxy strips
  this header and injects the upstream key for you; sending `x-api-key` from a browser is rejected
  by the vault's CORS preflight.
- **Use the proxied `/pw/*` path from browsers.** [LIVE] CORS for the browser case is handled by
  the vault and is already correct (`x-sgraph-access-token` allowed, `OPTIONS`→204, `ACAO:*`).
  Direct-to-instance access (raw IP, no proxy) is a separate mode with its own (minimal) CORS.

## 1. The two execution engines [NEW: async]

The same request/response contract is served by two interchangeable engines:

| Endpoint | Engine | Status |
|---|---|---|
| `POST /pw/sequence/execute` | sync Playwright internally | [LIVE/FIX] |
| `POST /pw/sequence/execute-async` | async Playwright internally | [NEW] |

Identical request and response schemas. The response carries `"engine": "sync" | "async"` [NEW] so
you can label runs and compare reliability/latency. Switch engines with a single config flag; fall
back per-verb if one engine misbehaves. Both are kept (by design) — neither is deprecated.

## 2. The request

```json
{
  "steps": [
    { "action": "navigate", "url": "https://example.com", "wait_until": "load" },
    { "action": "wait_for", "selector": "main", "timeout_ms": 8000 },
    { "action": "screenshot", "full_page": true }
  ],
  "capture_config":  { "screenshot": { "enabled": true, "sink": "inline" } },
  "sequence_config": { "halt_on_error": false, "default_step_timeout_ms": 15000 }
}
```

Steps are **flat** (fields at the top level of each step object). [LIVE]

## 3. Step verbs — authoritative set

Discover the live set + per-verb field schema at runtime via `GET /pw/health/capabilities` [NEW];
do **not** hand-maintain this list. Target vocabulary:

| Verb | Required | Optional | Status |
|---|---|---|---|
| `navigate` | `url` | `wait_until`, `timeout_ms` | [LIVE] |
| `click` | `selector` | `timeout_ms`, `button` | [LIVE] |
| `fill` | `selector`, `value` | `timeout_ms` | [LIVE] |
| `screenshot` | — | `full_page`, `selector`, `format` | [LIVE] |
| `get_content` | — | `selector`, `format` | [LIVE] |
| `get_url` | — | — | [LIVE] |
| `evaluate` | `expression` | — (allow-listed, read-only) | [LIVE] |
| `wait_for` | one of `selector`/`state`/`url` | `timeout_ms` | **[FIX]** — currently unimplemented; being added |
| `press` | `key` | `selector` | **[FIX]** |
| `select` | `selector`, `value` | — | **[FIX]** |
| `hover` | `selector` | `timeout_ms` | **[FIX]** |
| `scroll` | `direction`/`selector` | `pixels` | **[FIX]** |
| `set_viewport` | `width`, `height` | — | **[FIX]** |
| `dispatch_event` | `selector`, `event_type` | `event_init` | **[FIX]** |
| `expect_*` (assertions) | varies | — | [NEW] §7 |

> **Important for today:** `wait_for`, `press`, `select`, `hover`, `scroll`, `set_viewport`,
> `dispatch_event` are **not implemented yet** and currently abort the sequence. Your examples
> §5.2/5.3/5.4 depend on `wait_for`/`press` — they will work once [FIX] lands. Until then, restrict
> sequences to the [LIVE] verbs.

## 4. Error model — per-step isolation [LIVE for impl. verbs; FIX to make universal]

- A failing **step** never produces a non-2xx HTTP code. The call returns **200** with a populated
  `step_results`; the bad step is `status:"failed"` with an `error_message`. [LIVE for implemented
  verbs; [FIX] extends this guarantee to *any* uncaught step error]
- Non-2xx is reserved for **request-level** problems (bad auth → 401, malformed body → 422).
- `sequence_config.halt_on_error: true` → stop at first failure, remaining steps `skipped`.
  `false` → run all. [LIVE]
- Deadline (`default_step_timeout_ms` / sequence deadline) breach → remaining steps `skipped`. [LIVE]

## 5. The response [FIX: typed in OpenAPI]

```json
{
  "engine": "sync",
  "sequence_id": "safe-id_xxxx",
  "trace_id": "141ee092",
  "status": "completed",
  "total_duration_ms": 1472,
  "steps_total": 3, "steps_passed": 3, "steps_failed": 0, "steps_skipped": 0,
  "step_results": [
    { "step_id": "0", "step_index": 0, "action": "navigate",
      "status": "passed", "duration_ms": 817, "error_message": null, "artefacts": [] }
  ],
  "artefacts": [ /* sequence-level (terminal) artefacts, step_index: null */ ],
  "timings": { "playwright_start_ms": 518, "browser_launch_ms": 82, "steps_ms": 865, "browser_close_ms": 6, "total_ms": 1472 }
}
```

- `status` ∈ `completed | failed | partial`. [LIVE]
- Per-step artefacts live in `step_results[i].artefacts`; sequence-level (terminal/on-fail)
  artefacts live in top-level `artefacts` with `step_index: null`. [FIX: documented + terminal wired]
- The 200 response will be a **typed** `response_model` in `/openapi.json` (no longer `string`). [FIX]

## 6. Artefacts — self-describing objects [FIX/NEW]

Each artefact is self-describing:

```json
{
  "type": "screenshot",        // screenshot|video|pdf|har|trace|console_log|network_log|page_content
  "step_index": 1,             // null = terminal/sequence-level
  "sink": "inline",            // inline|vault|s3|local_file
  "content_type": "image/png",
  "encoding": "base64",        // base64|utf8|url
  "inline_b64": "iVBORw0K…",   // when sink=inline
  "vault_ref": { … },          // when sink=vault
  "s3_ref":    { … },          // when sink=s3
  "url":       "https://…",    // when a URL is available
  "size_bytes": 48213,
  "filename": "step-1.png"
}
```

- **`inline` returns real base64 bytes** with the correct `content_type`. [LIVE for screenshot step;
  [FIX] confirmed for both explicit-step and terminal capture]
- Default sink matrix: `screenshot=inline`; `video/har/trace=vault|s3` (large). Inline has a
  documented size cap. [NEW]
- `get_content`/`format:"html"` → `content_type:"text/html"`, `encoding:"utf8"`. [LIVE]

### 6.1 Capture semantics — the **hybrid** model [NEW]

This resolves your §4.1. We will implement the hybrid:

- An explicit **`screenshot` step** → capture at that point (`step_index` = the step). [LIVE]
- `capture_config.screenshot.enabled` (no step) → **terminal** screenshot of the final page
  (`step_index: null`). [NEW]
- `capture_config.screenshot_on_fail.enabled` → terminal screenshot only if the sequence ends
  failed. [NEW]
- `capture_config.page_content.enabled` → final DOM as a terminal artefact. [NEW]
- `har` / `console_log` / `network_log` → cover the whole sequence (context-level), terminal. [NEW]

So your §5.1 (`navigate` + `screenshot.enabled`, no screenshot step) will return one artefact:
`type:"screenshot"`, `step_index:null`, decodable inline PNG. [NEW]

## 7. Native assertions [NEW]

First-class verbs the service evaluates and reports pass/fail (no client-side faking):
`expect_selector_visible`, `expect_title_contains`, `expect_url_matches`, `expect_text`,
`expect_status`. Each is a step with `status: passed|failed` and an `error_message` describing the
mismatch.

## 8. Statelessness guarantee [LIVE, being hardened]

Every request gets a fresh browser + context, torn down at the end. No cookies, storage, sessions,
credentials, or temp files survive a request. Pass per-request `credentials` in the body if a flow
needs auth — the service never retains them. Safe to run many sequences concurrently.

## 9. Capabilities & health [NEW/FIX]

- `GET /pw/health/status` — cheap, returns `{version, status, browser_pool, uptime_ms}`. [FIX: typed]
- `GET /pw/health/capabilities` — **authoritative** verb list with per-verb field schema, supported
  `wait_until` states, screenshot formats, and capture sinks. [NEW] Your "Live capabilities" panel
  renders this directly; it replaces any hand-maintained verb list.
- `GET /pw/openapi.json`, `GET /pw/docs` — full spec + Swagger, prefix-correct. [LIVE]

## 10. Explore (not committed) [NEW, separate design]

Live screencast (watch the running browser) and time-boxed CDP remote-control are of high interest
but architecturally belong with the **visible-browser** specs (vnc/firefox), not this stateless
headless service. They'll be designed separately, not bolted onto `/sequence/execute`.

---

## 11. The question for you (Workbench team)

**If the [FIX] and [NEW] items above are implemented exactly as described, does this do what the
Workbench needs?** In particular:

1. Are the **hybrid capture semantics** (§6.1) what you expect for the "no screenshot step but
   `screenshot.enabled`" case?
2. Is the **artefact object shape** (§6) renderable as-is by your inline viewer?
3. Is `GET /health/capabilities` (§9) the right contract for your "Live capabilities" panel?
4. Is the **per-step error model** (§4) sufficient, or do you need richer error typing
   (e.g. `error_type: timeout|selector_not_found|navigation_failed`)?
5. Do you need the **async engine** (§1) on day one, or is a correct sync path enough to unblock you
   while async is built in parallel?

See `03__questions-for-the-workbench-agent.md` for the full list.
