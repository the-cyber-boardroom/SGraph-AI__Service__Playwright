---
title: "05 — JS API (proposed SDK + window.* console API)"
file: 05__js-api.md
author: Architect (Claude)
date: 2026-06-21
repo: SGraph-AI__Service__Playwright @ dev (root version: v0.2.63)
status: PROPOSED — design proposal, BLOCKED on precedent (Q1). No runtime code.
parent: README.md
covers: "User point (f) — JS API support"
---

# 05 — JS API

Covers **point (f)**: JavaScript-API support, in two layers — (1) a small JS
client/SDK that wraps the HTTP endpoints, and (2) an in-page programmable `window.*`
API so the console itself is scriptable from devtools.

> ⚠ **ALIGN-ON-PRECEDENT — this brief is a SHAPE PROPOSAL, not a locked API.** See
> the OPEN QUESTION block (§1). The cross-repo "how we did the JS API in our other
> tools" precedent is **not available in this session**. The method names,
> namespacing, and packaging below are a reasonable house-style proposal to be
> ratified — or replaced — once the precedent repo is supplied.

---

## 1. OPEN QUESTION (Q1) — BLOCKING for the final API shape

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  OPEN QUESTION — JS-API precedent repo                                         ║
║                                                                                ║
║  The mission references "how we did the JS API in our other tools." That       ║
║  precedent is NOT reachable from this session. Before locking method names,    ║
║  the global namespace, promise vs callback style, ESM vs IIFE packaging, or    ║
║  whether the SDK ships as a separately-served .js asset, the operator must     ║
║  point at:                                                                     ║
║                                                                                ║
║    • the precedent repo + the canonical client file path, and                 ║
║    • whether the house style is `window.<name>` global, an ESM export, or both ║
║                                                                                ║
║  Until then, §3-§5 below are a PROPOSAL aligned to the ONE in-repo precedent   ║
║  found (the admin-site ApiClient, §2). Phases 1-4 + 6 of the implementation    ║
║  plan do NOT depend on this answer; only the JS-API phase (Phase 5) does.      ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. In-repo precedent found (the only one)

A repo sweep found **no public Playwright JS SDK** — only:

| File | What it is | Relevance |
|------|-----------|-----------|
| `sgraph_ai_service_playwright__api_site/shared/api-client.js` | An **ESM `class ApiClient`** (`api-client.js:8-46`): `apiUrl`/`apiKey` from localStorage, `request(method,path,body)`, `get/post/delete`, sends `X-API-Key` (`:25`), dispatches `sg-auth-required` on 401 (`:33`), throws `HTTP <status>: <text>` on non-OK (`:38`). Exported singleton `apiClient` (`:48`). | This is the **house pattern** for "wrap the HTTP API in JS" in THIS repo. The proposed SDK mirrors its conventions. It is admin-site-internal, NOT a published Playwright SDK. |
| `sgraph_ai_service_playwright__api_site/shared/components/sg-api-client.js` | A web-component wrapper (~21 lines) over the above | UI glue, not an SDK |
| `Routes__Index.py:26` + `:287-583` | The inline `<script>` in the test page (`window.API_BASE`, `post()` helper) | The current "JS API" is just this inline script — no reusable client |

**Conclusion to record:** beyond the inline script in `Routes__Index.py` and the
admin-site `ApiClient`, **no JS client/SDK exists in this repo.** The proposal below
extends the `ApiClient` shape to the Playwright surface; the precedent question (Q1)
decides whether that is the right shape or whether an external house style supersedes
it.

---

## 3. Layer 1 — proposed SDK (`sg-playwright-client.js`)

A small dependency-free client wrapping the 21 endpoints, mirroring `api-client.js`
conventions (ESM, localStorage-backed key, 401 event, `HTTP <status>` errors) but
**auth-mode aware** (the Playwright surface has the `X-API-Key` vs
`x-sgraph-access-token` split that the admin site does not — `use-sg-playwright/SKILL.md`).

```js
// PROPOSAL — shape pending Q1
export class SgPlaywrightClient {
  constructor({ baseUrl, token, authMode = 'apiKey' } = {}) {
    this.baseUrl  = (baseUrl || window.location.origin).replace(/\/$/, '');
    this.token    = token || '';
    this.authMode = authMode;            // 'apiKey' (X-API-Key) | 'proxy' (x-sgraph-access-token)
  }
  // health
  health()        { return this.#get('/health/status'); }
  info()          { return this.#get('/health/info'); }
  capabilities()  { return this.#get('/health/capabilities'); }
  metrics()       { return this.#text('/metrics'); }
  // screenshot
  screenshot(body)       { return this.#post('/screenshot', body); }
  screenshotBatch(body)  { return this.#post('/screenshot/batch', body); }
  // sequence / inspect
  sequence(body)  { return this.#post('/sequence/execute', body); }
  inspect(body)   { return this.#post('/inspect', body); }
  // browser one-shots
  browser(verb, body) { return this.#post(`/browser/${verb}`, body); }   // navigate|click|fill|get-content|get-url|screenshot
  // session
  sessionOpen(body)            { return this.#post('/session/open', body); }
  sessionAct(id, body)         { return this.#post(`/session/${id}/act`, body); }
  sessionProbe(id, body)       { return this.#post(`/session/${id}/probe`, body); }
  sessionClose(id)             { return this.#post(`/session/${id}/close`, {}); }
  // ── private ──
  #headers() {
    const h = { 'Content-Type': 'application/json' };
    if (this.token) h[this.authMode === 'proxy' ? 'x-sgraph-access-token' : 'X-API-Key'] = this.token;
    return h;
  }
  async #post(p, b) { return this.#req('POST', p, b); }
  async #get(p)     { return this.#req('GET', p); }
  async #req(m, p, b) {
    const r = await fetch(this.baseUrl + p, { method: m, headers: this.#headers(),
                                              body: b === undefined ? undefined : JSON.stringify(b) });
    if (r.status === 401) { document.dispatchEvent(new CustomEvent('sg-auth-required')); throw new Error('401 — wrong auth header for this path?'); }
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
    const ct = r.headers.get('content-type') || '';
    return ct.includes('application/json') ? r.json()
         : ct.includes('image/png')        ? r.blob()      // /browser/screenshot returns raw PNG
         :                                   r.text();      // /metrics is text/plain
  }
  async #text(p) { return (await fetch(this.baseUrl + p, { headers: this.#headers() })).text(); }
}
```

Notes:
- Handles the **three response content types** the surface actually returns: JSON
  (most), raw `image/png` (`/browser/screenshot`, with `X-*-Ms` timing headers), and
  `text/plain` (`/metrics`).
- Auth-mode aware (Decision #7) — the SDK's one job the admin client doesn't have.
- **Packaging is the open question:** served as a sibling route
  (`GET /sg-playwright-client.js`) so external pages can `import`? Inlined only? Both?
  Decided by Q1.

---

## 4. Layer 2 — in-page programmable `window.*` console API

So the console is scriptable from devtools and from the share-link/automation paths.
The page exposes a namespaced global wrapping the same SDK plus console actions.

```js
// PROPOSAL — global name pending Q1 (window.sgp vs window.sgPlaywright vs ...)
window.sgp = {
  client: <SgPlaywrightClient bound to the current auth panel state>,
  run(workflowOrBody),        // execute a workflow file or a raw request body, render in the result pane
  loadExample(id),            // load a gallery workflow (W1..W9) into the active builder
  exportWorkflow(),           // return the current builder state as a workflow file (brief 03)
  importWorkflow(obj),        // load a workflow file into the builder
  setAuth({ token, authMode }),
  capabilities(),             // → the cached bootstrap capabilities
  version,                    // service_version from /health/info
};
```

This makes every console action driveable programmatically — e.g.
`await sgp.run(sgp.loadExample('W3'))` from devtools, or an automation harness opening
`GET /` and scripting `window.sgp`. It also gives brief 06's integration tests a
**UI-surface execute path** to smoke-test (the test drives `window.sgp.run(...)` in a
headless browser, see brief 06 §4).

---

## 5. Constraints any final shape must honour

Regardless of how Q1 resolves:

1. **Dependency-free, no build step** (Decision #1) — vanilla ES2020, served as-is.
2. **Auth-mode aware** — the `X-API-Key` / `x-sgraph-access-token` split is mandatory;
   a single hard-coded header reproduces the #1 first-attempt 401.
3. **Secret-safe** — the SDK never logs the token; `window.sgp` exposes `setAuth` but
   does not expose the stored token as a readable property.
4. **Type_Safe N/A** — this is browser JS, not Python; CLAUDE.md's Type_Safe/no-Pydantic
   rules govern the *service*, not the served client. The client must still avoid
   inventing field names: every body it sends matches a `Schema__*` (briefs 02/03).
5. **No new endpoint to serve it** unless Q1 says ship it as an asset — and if so, it's
   a static `GET` route returning the `.js`, added to `Fast_API__Playwright__Service`
   alongside `Routes__Index`, excluded from nothing (public, like `GET /`).

---

## 6. Recommendation

Adopt the `SgPlaywrightClient` shape (§3) — it is a minimal, faithful extension of the
**only** in-repo precedent (`api-client.js`) — as the **interim** design, and treat Q1
as a ratification gate: if the operator's other-tools precedent differs, rename/repackage
to match before Phase 5 implements. Phases 1-4 and 6 proceed regardless; the console is
fully usable without any SDK (the inline script suffices), so the JS-API layer is
purely additive and never on the critical path.
