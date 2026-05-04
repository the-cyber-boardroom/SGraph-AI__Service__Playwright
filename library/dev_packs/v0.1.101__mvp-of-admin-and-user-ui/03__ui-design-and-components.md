# 03 — UI Design and Components

**Status:** PROPOSED
**Read after:** `README.md`, `01__mvp-scope-and-flows.md`
**Audience:** Sonnet implementing the JS/HTML side
**Verified against:** `dev` HEAD `7e72431`, existing `__api_site/` (~405 lines, 6 files)

---

## What this doc gives you

The complete UI implementation plan: folder layout, every component's API (props, events), every module's responsibility, the page-controller logic for both UIs, the connection panel, the polling design, the test pattern. All concrete enough that you can start coding without making structural decisions.

Total UI: ~5 dev-days for one developer.

## Pre-flight

Read these before coding:

- `sgraph_ai_service_playwright__api_site/index.html` (66 lines), `app.js` (74 lines), `style.css` (169 lines), `storage.js` (44 lines), `cookie.js` (19 lines), `health.js` (33 lines) — the existing static app. The patterns there (X-API-Key flow, localStorage shape, link generation) carry forward into the new code; we are evolving, not rebuilding from scratch.
- The existing `style.css` is the visual baseline. The new shared `tokens.css` extracts its variables and keeps the look consistent.

## Folder layout — final shape

```
sgraph_ai_service_playwright__api_site/
├── index.html                  ← landing page: [Admin] / [Provision] buttons
├── style.css                   ← existing — kept as-is for index.html
│
├── shared/
│   ├── tokens.css              ← NEW — CSS custom properties (extracted from style.css)
│   ├── api-client.js           ← NEW — the only fetch boundary
│   ├── catalog.js              ← NEW — caches /catalog/types
│   ├── poll.js                 ← NEW — health-poll loop with back-off
│   ├── storage.js              ← NEW — moved + tightened from root storage.js
│   └── components/
│       ├── sg-api-client.js    ← Web Component wrapping api-client.js
│       ├── sg-auth-panel.js
│       ├── sg-header.js
│       ├── sg-stack-grid.js
│       ├── sg-stack-card.js
│       ├── sg-create-modal.js
│       └── sg-toast-host.js
│
├── admin/
│   ├── index.html              ← cross-stack dashboard
│   ├── admin.js                ← page controller
│   └── admin.css               ← admin-only styles (small)
│
├── user/
│   ├── index.html              ← per-type "Start" cards
│   ├── user.js                 ← page controller
│   └── user.css                ← user-only styles (small)
│
├── app.js                      ← existing — kept until next pass deletes it
├── cookie.js                   ← existing — kept; pattern reused for service-origin auth
├── health.js                   ← existing — kept until next pass folds it into shared/
└── storage.js                  ← existing — kept; new code uses shared/storage.js
```

Files marked NEW are this brief's deliverables. Existing files in the root are left untouched in this PR series — the next housekeeping brief can fold them into `shared/` or delete them.

## The non-negotiables (re-stated for the UI side)

1. **Only `<sg-api-client>` calls `fetch`.** `grep -r "fetch(" sgraph_ai_service_playwright__api_site/` should hit only `shared/api-client.js`.
2. **Only `<sg-api-client>` and `<sg-auth-panel>` touch `localStorage`.** Same `grep` rule.
3. **Components are dumb renderers.** No fetch inside components, no routing. Page controllers wire components together.
4. **No Shadow DOM** for the MVP. Components extend `HTMLElement` and append to `this` directly. CSS via shared `tokens.css` and per-component `<style>` tags inside the component (or in the per-page CSS file).
5. **No build step.** Native ES modules. Each component is a `.js` file with `export default class`, imported via `<script type="module">`.
6. **No third-party JS.** No React, Vue, Lit, or framework. Native Web Components only.
7. **`CustomEvent` for all component-to-controller communication.** Detail is always a plain object. Names are prefixed `sg-`.
8. **Vanilla `fetch`.** No axios, no client lib.

## Module: `shared/api-client.js`

The fetch boundary. Used by both page controllers and by `<sg-api-client>` (which is just a thin Web Component wrapper for HTML-driven access).

```javascript
// shared/api-client.js

const STORAGE_KEY = 'sg_playwright_config';                     // re-uses the existing key

class ApiClient {
  constructor() {
    const cfg = this._loadConfig();
    this.baseUrl    = cfg.baseUrl    || window.location.origin;
    this.apiKey     = cfg.apiKey     || '';
    this.apiKeyName = cfg.apiKeyName || 'X-API-Key';
  }

  // ─── config persistence ─────────────────────────────────────────

  _loadConfig() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (_) { return {}; }
  }

  saveConfig({ baseUrl, apiKey, apiKeyName }) {
    this.baseUrl    = baseUrl    || this.baseUrl;
    this.apiKey     = apiKey     || this.apiKey;
    this.apiKeyName = apiKeyName || this.apiKeyName;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        baseUrl    : this.baseUrl,
        apiKey     : this.apiKey,
        apiKeyName : this.apiKeyName,
      }));
    } catch (_) {}
  }

  // ─── fetch primitive ────────────────────────────────────────────

  async _request(method, path, body = null) {
    const url     = `${this.baseUrl}${path}`;
    const headers = { 'Accept': 'application/json' };
    if (this.apiKey)  headers[this.apiKeyName] = this.apiKey;
    if (body !== null) headers['Content-Type'] = 'application/json';

    let response;
    try {
      response = await fetch(url, {
        method,
        headers,
        body: body !== null ? JSON.stringify(body) : null,
      });
    } catch (e) {
      throw { kind: 'network', message: e.message, url };
    }

    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : null; }
    catch (_) { data = { raw: text }; }

    if (!response.ok) {
      throw { kind: 'http', status: response.status, body: data, url };
    }
    return data;
  }

  // ─── catalog ────────────────────────────────────────────────────

  getCatalogTypes()                  { return this._request('GET', '/catalog/types' ); }
  getCatalogStacks(typeFilter = '')  {
    const qs = typeFilter ? `?type=${encodeURIComponent(typeFilter)}` : '';
    return this._request('GET', `/catalog/stacks${qs}`);
  }

  // ─── per-type lifecycle ─────────────────────────────────────────

  listStacks    (type)              { return this._request('GET'   , `/${type}/stacks`); }
  getStackInfo  (type, name)        { return this._request('GET'   , `/${type}/stack/${encodeURIComponent(name)}`); }
  createStack   (type, body)        { return this._request('POST'  , `/${type}/stack`, body); }
  deleteStack   (type, name)        { return this._request('DELETE', `/${type}/stack/${encodeURIComponent(name)}`); }
  getStackHealth(type, name)        { return this._request('GET'   , `/${type}/stack/${encodeURIComponent(name)}/health`); }

  // ─── auth verification ──────────────────────────────────────────

  ping() { return this._request('GET', '/'); }                    // hits the osbot-fast-api root, surfaces 401 if key wrong
}

export const apiClient = new ApiClient();                         // module-level singleton
export default ApiClient;                                          // for tests / extension
```

**Error contract:** every method either resolves with the parsed JSON body or throws `{ kind: 'network'|'http', status, body, message, url }`. Page controllers pattern-match on `kind` and `status`.

## Module: `shared/catalog.js`

```javascript
// shared/catalog.js — caches /catalog/types for the page lifetime

import { apiClient } from './api-client.js';

let cached = null;

export async function getCatalog() {
  if (cached) return cached;
  cached = await apiClient.getCatalogTypes();
  return cached;
}

export function clearCatalogCache() { cached = null; }            // call from <sg-auth-panel> after key change
```

The catalog is small (~5 entries), changes rarely, and the UI reads it on every page load. One in-memory cache per page lifecycle is sufficient.

## Module: `shared/poll.js`

```javascript
// shared/poll.js — health-poll loop with back-off, cancellation, visibility-pause

import { apiClient } from './api-client.js';

const PHASE_FAST_UNTIL  =  30_000;     // 30s @ 3s
const PHASE_MED_UNTIL   = 120_000;     // next 90s @ 5s
const PHASE_SLOW_AFTER  = 120_000;     // beyond @ 10s
const NETWORK_ERR_LIMIT = 3;            // consecutive errors before "lost"

export function startHealthPoll({
  type,
  name,
  maxWallClockMs,                       // 300_000 for linux/elastic, 600_000 for docker
  onTick,                               // ({health}) → void
  onReady,                              // ({health}) → void
  onConnectionLost,                     // ({lastHealth, sinceMs}) → void
  onConnectionRestored,                 // ({health}) → void
  onTimeout,                            // ({lastHealth}) → void
}) {
  const startedAt = Date.now();
  let   stopped   = false;
  let   netErrs   = 0;
  let   lastHealth = null;

  function cadenceFor(elapsedMs) {
    if (elapsedMs < PHASE_FAST_UNTIL) return  3_000;
    if (elapsedMs < PHASE_MED_UNTIL ) return  5_000;
    return                                    10_000;
  }

  async function tick() {
    if (stopped) return;
    if (document.visibilityState !== 'visible') {
      // pause; resume on visibilitychange handler below
      return;
    }
    const elapsed = Date.now() - startedAt;
    if (elapsed > maxWallClockMs) {
      onTimeout({ lastHealth });
      stopped = true;
      return;
    }
    try {
      const health = await apiClient.getStackHealth(type, name);
      if (netErrs >= NETWORK_ERR_LIMIT) onConnectionRestored({ health });
      netErrs    = 0;
      lastHealth = health;
      onTick({ health });
      if (health.healthy) {
        onReady({ health });
        stopped = true;
        return;
      }
    } catch (err) {
      netErrs += 1;
      if (netErrs === NETWORK_ERR_LIMIT) {
        onConnectionLost({ lastHealth, sinceMs: elapsed });
      }
    }
    if (!stopped) setTimeout(tick, cadenceFor(Date.now() - startedAt));
  }

  function onVisibility() {
    if (document.visibilityState === 'visible' && !stopped) tick();
  }
  document.addEventListener('visibilitychange', onVisibility);

  tick();

  return {
    stop() {
      stopped = true;
      document.removeEventListener('visibilitychange', onVisibility);
    },
  };
}
```

## Components

All components extend `HTMLElement`, define `customElements.define('sg-foo', SgFoo)`, and follow this skeleton:

```javascript
// shared/components/sg-foo.js

class SgFoo extends HTMLElement {
  constructor() {
    super();
    this._state = {};
  }

  // ─── attributes / props ────────────────────────────────────────
  static get observedAttributes() { return ['some-attr']; }
  attributeChangedCallback(name, _, value) { this._state[name] = value; this._render(); }

  // properties (set via JS, not as attributes)
  set data(value) { this._state.data = value; this._render(); }
  get data()      { return this._state.data; }

  // ─── lifecycle ─────────────────────────────────────────────────
  connectedCallback   () { this._render(); }
  disconnectedCallback() { /* tear down listeners, polls, etc. */ }

  // ─── render ────────────────────────────────────────────────────
  _render() {
    if (!this._state.data) return;                                // no-op until data set
    this.innerHTML = `<div>...</div>`;
    this.querySelector('button')?.addEventListener('click', () => {
      this.dispatchEvent(new CustomEvent('sg-foo-click', {
        detail  : { /* … */ },
        bubbles : true,
      }));
    });
  }
}
customElements.define('sg-foo', SgFoo);
export default SgFoo;
```

### `<sg-api-client>` (component wrapper around `api-client.js`)

A no-render Web Component that exposes the singleton `apiClient` to controllers via `document.querySelector('sg-api-client').client`. Declared once per page in the HTML head. Its only job is to make the client discoverable and to fire `sg-auth-required` on 401 responses (so `<sg-auth-panel>` can listen).

**Properties:**

| Prop | Description |
|---|---|
| `client` | the singleton `ApiClient` |

**Events:**

| Event | When |
|---|---|
| `sg-auth-required` | Any request returned 401 — page controllers listen at `document` level |

**Implementation:** wraps each method on `apiClient`, dispatches `sg-auth-required` on 401, otherwise re-raises. ~30 lines.

### `<sg-auth-panel>`

The connection drawer. Form for base URL + API key + key name. Stores them via `apiClient.saveConfig()`.

**Attributes:**

| Attr | Description |
|---|---|
| `open` | when present, the panel is visible |

**Properties:** none. Reads/writes via `apiClient`.

**Events:**

| Event | Detail | When |
|---|---|---|
| `sg-auth-saved` | `{ baseUrl, apiKeyName }` (no key value in detail) | After successful save + ping |
| `sg-auth-cancelled` | — | User clicked [Cancel] |

**Behaviour:**

1. On `connectedCallback`, render the form pre-populated from `apiClient`.
2. `[Save & verify]` button: writes to `apiClient`, calls `apiClient.ping()`, shows ✓ on success or red error on failure.
3. On success, dispatch `sg-auth-saved` and remove the `open` attribute (page controller can collapse).
4. Listens at `document` for `sg-auth-required` events from `<sg-api-client>`; sets `open`.

**Visual:** lifted from existing `index.html`'s `#config-card`. Same fields, same layout.

### `<sg-header>`

The shared top bar. Title, environment badge, [Settings ⚙] button, version display.

**Attributes:**

| Attr | Description |
|---|---|
| `title` | Page title shown alongside the branding |
| `subtitle` | Optional secondary line |

**Properties:**

| Prop | Description |
|---|---|
| `version` | shown on the right; populated from `/openapi.json`'s `info.version` by the page controller |

**Events:**

| Event | When |
|---|---|
| `sg-settings-click` | User clicked the [Settings ⚙] button |

### `<sg-stack-grid>`

The core layout component. Different `mode` attribute renders different shapes.

**Attributes:**

| Attr | Values | Description |
|---|---|---|
| `mode` | `admin-table` \| `type-cards` \| `user-cards` \| `user-active` | Render shape |

**Properties:**

| Prop | Description |
|---|---|
| `types` | catalog entries — for `type-cards` and `user-cards` modes |
| `stacks` | array of `Schema__Stack__Summary` — for `admin-table` and `user-active` modes |
| `loading` | shows skeleton placeholders |

**Events:**

| Event | Detail | When |
|---|---|---|
| `sg-stack-action` | `{ action, type, name }` | User clicked a row action (Info / Stop / Details) |
| `sg-type-action` | `{ action: 'start', type }` | User clicked [Start] on a tile |

**Render shapes:**

- **`admin-table`** — HTML table of running stacks across all types. Columns: Type / Name / State / Public IP / Uptime / Actions.
- **`type-cards`** — small horizontal strip of type tiles (one per available type) with availability indicator. Used in admin's "Stack Types" section.
- **`user-cards`** — large vertical/grid layout of type cards with description, expected boot time, [Start] button. Disabled-styled if `available=false` ("coming soon").
- **`user-active`** — horizontal strip of running stacks for the user UI's active section. Compact rows.

One component, four modes, because each is a thin variation of "render a list of things in CSS Grid". Splitting into four components is overkill for the MVP.

### `<sg-stack-card>`

One running stack, used inside `<sg-stack-grid mode="user-active">` and stand-alone in detail contexts.

**Attributes:**

| Attr | Description |
|---|---|
| `compact` | grid mode (less detail) vs detail mode (full) |

**Properties:**

| Prop | Description |
|---|---|
| `summary` | a `Schema__Stack__Summary` object |

**Events:**

| Event | Detail | When |
|---|---|---|
| `sg-card-action` | `{ action: 'details'\|'stop', type, name }` | User clicked a button |

**Visual cues:**

| State (per `Schema__Stack__Summary.state`, normalised) | Colour | Animation |
|---|---|---|
| `PENDING` / `STARTING` | amber | pulse |
| `RUNNING` / `READY` | green | static |
| `STOPPING` / `SHUTTING-DOWN` | amber | pulse |
| `STOPPED` / `TERMINATED` | grey | static (rarely shown — list filters these) |
| `UNKNOWN` | red | static |

State name normalisation: `state` from the catalog summary is a free-form string (it's the rendered name of the per-type enum). Map known prefixes to colour buckets; default to `UNKNOWN` styling for anything else.

### `<sg-create-modal>`

The provisioning workflow's centrepiece. Renders one of three internal states:

1. **`form`** — type-specific create inputs (region, instance type, max hours, advanced disclosure)
2. **`progress`** — progress bar polling the health endpoint, showing live state transitions
3. **`ready`** — the "stack is up" panel with public IP, SSM command, copy buttons

**Attributes:**

| Attr | Description |
|---|---|
| `open` | when present, modal is visible |

**Properties:**

| Prop | Description |
|---|---|
| `type` | which stack type — `linux` / `docker` / `elastic` |
| `catalogEntry` | the corresponding catalog entry (used for `expected_boot_seconds`, `default_*` values) |

**Events:**

| Event | Detail | When |
|---|---|---|
| `sg-create-submit` | `{ type, body }` | User clicked [Start →] on the form |
| `sg-create-cancel` | `{ type, name? }` | User cancelled — name is set if cancelling during boot |
| `sg-create-done` | `{ type, name, info }` | User clicked [Done] on the ready panel |
| `sg-create-stop` | `{ type, name }` | User clicked [Stop] on the ready panel |

**Internal state machine:**

```
   form ──[submit]──► progress ──[healthy]──► ready
     │                   │                      │
     │                   ├─[cancel during boot]─┤
     │                   │                      │
     │                   ├──[timeout]────────► (timeout view inside progress)
     │                   │
     ├──[cancel before submit]──► closed (open removed)
     │                                          │
     └──[done from ready]────────────────────► closed
                                                │
     [stop from ready]──► (delete in flight) ──► closed
```

The page controller owns the create flow:

```javascript
// admin.js / user.js controller logic
modal.addEventListener('sg-create-submit', async (e) => {
  const { type, body } = e.detail;
  const created = await apiClient.createStack(type, body);
  modal.startProgress({ name: created.stack_info.stack_name, info: created.stack_info });
  // modal.startProgress() begins polling internally, fires sg-create-done when ready
});
```

The modal owns the polling once it transitions to `progress` — it imports `startHealthPoll` directly. Event flow stays clean: controller hands off when create succeeds, modal manages the rest until done/cancel/stop.

### `<sg-toast-host>`

Floating region for transient messages. Listens at `document` for `sg-toast` events.

**Properties / events:** none — passive listener.

**API:**

```javascript
// from anywhere:
document.dispatchEvent(new CustomEvent('sg-toast', {
  detail: { kind: 'error'|'info'|'success', message: '...', durationMs: 5000 }
}));
```

One per page. Both controllers fire toasts.

## Page controller: `admin/admin.js`

```javascript
import { apiClient }    from '../shared/api-client.js';
import { getCatalog }   from '../shared/catalog.js';
import '../shared/components/sg-api-client.js';
import '../shared/components/sg-auth-panel.js';
import '../shared/components/sg-header.js';
import '../shared/components/sg-stack-grid.js';
import '../shared/components/sg-create-modal.js';
import '../shared/components/sg-toast-host.js';

const REFRESH_INTERVAL_MS = 10_000;

(async function main() {
  const catalog = await getCatalog();

  const typesGrid  = document.querySelector('sg-stack-grid[mode="type-cards"]');
  const stacksGrid = document.querySelector('sg-stack-grid[mode="admin-table"]');
  const modal      = document.querySelector('sg-create-modal');

  typesGrid.types  = catalog.entries;

  async function refreshActive() {
    try {
      const list = await apiClient.getCatalogStacks();
      stacksGrid.stacks = list.stacks;
    } catch (err) {
      // 401 already handled by sg-api-client → sg-auth-panel
      // others: toast
      if (err.kind !== 'http' || err.status !== 401) {
        document.dispatchEvent(new CustomEvent('sg-toast', {
          detail: { kind: 'error', message: `Could not refresh: ${err.message || err.body?.detail}`, durationMs: 4000 }
        }));
      }
    }
  }

  // Wire events
  typesGrid.addEventListener('sg-type-action', (e) => {
    const entry = catalog.entries.find(x => x.type_id === e.detail.type);
    modal.type         = e.detail.type;
    modal.catalogEntry = entry;
    modal.setAttribute('open', '');
  });

  stacksGrid.addEventListener('sg-stack-action', async (e) => {
    if (e.detail.action === 'stop') {
      try {
        await apiClient.deleteStack(e.detail.type, e.detail.name);
        document.dispatchEvent(new CustomEvent('sg-toast', {
          detail: { kind: 'success', message: `Stopped ${e.detail.name}`, durationMs: 3000 }
        }));
        refreshActive();
      } catch (err) { /* toast */ }
    }
  });

  modal.addEventListener('sg-create-done',  refreshActive);
  modal.addEventListener('sg-create-stop',  refreshActive);
  modal.addEventListener('sg-create-cancel', refreshActive);

  // Poll the active list while the page is visible
  refreshActive();
  setInterval(() => {
    if (document.visibilityState === 'visible') refreshActive();
  }, REFRESH_INTERVAL_MS);
})();
```

## Page controller: `user/user.js`

Same shape, simpler. Differences:

- Reads `catalog.entries` and feeds to `<sg-stack-grid mode="user-cards">`.
- Calls `apiClient.getCatalogStacks()` for the active strip (`<sg-stack-grid mode="user-active">`).
- `sg-type-action` opens the modal (same flow as admin).
- No "recent activity" section.

## CSS strategy

```
shared/tokens.css     ← :root custom properties (colours, spacing, fonts, radii)
shared/components/    ← each component embeds <style> with token-referenced rules
admin/admin.css       ← table-specific layout for admin-table mode
user/user.css         ← grid layout for user-cards mode
```

Tokens are extracted from the existing `style.css`. Sample (final values come from existing palette, this is the shape):

```css
/* shared/tokens.css */
:root {
  --sg-color-bg:        #0e0e10;
  --sg-color-fg:        #e8e8e9;
  --sg-color-card:      #1a1a1c;
  --sg-color-border:    #28282b;
  --sg-color-accent:    #3aa6ff;
  --sg-color-success:   #2bb673;
  --sg-color-warning:   #d49a2a;
  --sg-color-error:     #c14545;
  --sg-radius:          6px;
  --sg-spacing:         8px;
  --sg-spacing-lg:      16px;
  --sg-font-mono:       'JetBrains Mono', 'IBM Plex Mono', monospace;
}
```

Each component's `<style>` references tokens — so changing the palette is one file. No theming layer in the MVP; the structure supports adding one later.

## Testing approach

The MVP is too small to justify a full Vitest + jsdom harness in the same PR. **Two layers of verification:**

1. **Unit-style component checks** in plain HTML test pages under `tests/manual/` (or similar), one per component. Each loads the component, sets properties, and asserts on rendered DOM via simple inline scripts. These run in any browser; not part of CI for the MVP. Pattern:

```html
<!-- tests/manual/sg-stack-card.html -->
<!DOCTYPE html>
<html>
<body>
<sg-stack-card></sg-stack-card>
<script type="module">
  import '../../shared/components/sg-stack-card.js';
  const el = document.querySelector('sg-stack-card');
  el.summary = { type_id: 'linux', stack_name: 'linux-quiet-fermi', state: 'RUNNING', public_ip: '1.2.3.4', uptime_seconds: 120 };
  // visually inspect
</script>
</body></html>
```

2. **End-to-end smoke check** documented in the brief's acceptance criteria — boot the backend locally, open both UIs, run through the demo flow. This is the test that matters for the MVP.

A full automated test harness (Vitest, Playwright e2e) is its own follow-up brief once the UI shape stabilises.

## Layout of the two HTML pages

**`admin/index.html`:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SG Playwright — Admin</title>
  <link rel="stylesheet" href="../shared/tokens.css">
  <link rel="stylesheet" href="admin.css">
</head>
<body>
  <sg-api-client></sg-api-client>
  <sg-toast-host></sg-toast-host>
  <sg-auth-panel></sg-auth-panel>

  <sg-header title="Admin Dashboard" subtitle="All stacks, all types"></sg-header>

  <main>
    <section>
      <h2>Active stacks</h2>
      <sg-stack-grid mode="admin-table"></sg-stack-grid>
    </section>

    <section>
      <h2>Stack types</h2>
      <sg-stack-grid mode="type-cards"></sg-stack-grid>
    </section>

    <section>
      <h2>Recent activity</h2>
      <ul id="activity-log"></ul>
    </section>
  </main>

  <sg-create-modal></sg-create-modal>

  <script type="module" src="admin.js"></script>
</body>
</html>
```

**`user/index.html`** — same shape, different copy and grid modes:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SG Playwright — Provisioning</title>
  <link rel="stylesheet" href="../shared/tokens.css">
  <link rel="stylesheet" href="user.css">
</head>
<body>
  <sg-api-client></sg-api-client>
  <sg-toast-host></sg-toast-host>
  <sg-auth-panel></sg-auth-panel>

  <sg-header title="Provisioning" subtitle="Start an environment"></sg-header>

  <main>
    <section>
      <h2>Start a new environment</h2>
      <sg-stack-grid mode="user-cards"></sg-stack-grid>
    </section>

    <section>
      <h2>Your active stacks</h2>
      <sg-stack-grid mode="user-active"></sg-stack-grid>
    </section>
  </main>

  <sg-create-modal></sg-create-modal>

  <script type="module" src="user.js"></script>
</body>
</html>
```

**Root `index.html`** evolves into a small landing page (replace existing content):

```html
<!-- sgraph_ai_service_playwright__api_site/index.html -->
<main class="landing">
  <h1>SG Playwright</h1>
  <p>Choose your view:</p>
  <div class="landing-actions">
    <a href="./admin/" class="btn btn--primary">Admin Dashboard</a>
    <a href="./user/"  class="btn btn--accent">Provision an environment</a>
  </div>
</main>
```

## Effort breakdown

| Item | Effort |
|---|---|
| `tokens.css` + extracting from existing `style.css` | 0.25d |
| `shared/api-client.js` (+ smoke test against running backend) | 0.5d |
| `shared/catalog.js`, `shared/poll.js` | 0.25d |
| `<sg-api-client>`, `<sg-auth-panel>`, `<sg-header>`, `<sg-toast-host>` | 1d |
| `<sg-stack-grid>` (4 modes) | 1d |
| `<sg-stack-card>` | 0.25d |
| `<sg-create-modal>` (state machine: form/progress/ready) | 1d |
| `admin/index.html` + `admin.js` + `admin.css` | 0.5d |
| `user/index.html` + `user.js` + `user.css` | 0.5d |
| Manual test pages, end-to-end demo run, polish | 0.5d |

**~5 dev-days** for one developer. Two developers in parallel: ~3 days elapsed if the component ownership splits cleanly.

## Sequencing with the backend PRs

```
Backend dev:  PR-1 ──► PR-2 ──► PR-3
                       │
UI dev:       (start here, against PR-1's mounted routes)
              tokens.css → api-client → poll → catalog
              → components → page controllers → demo run
              ↓
              UI integrates with /catalog/* once PR-2 lands
              ↓
              Elastic tile flips live once PR-3 lands
```

The UI dev can start as soon as PR-1 is merged (against linux + docker only). The catalog endpoint's absence shows up as a single fetch error that gates the type grid; everything else works. PR-2 brings the type grid alive. PR-3 makes the elastic tile transition from "coming soon" to live.

If you have one developer, the order is: PR-1 → start UI scaffolding → PR-2 → finish components → PR-3 → polish + demo.

## Acceptance for the UI

A reviewer should be able to confirm all of these:

1. `grep -r "fetch(" sgraph_ai_service_playwright__api_site/` returns hits **only** in `shared/api-client.js`.
2. `grep -r "localStorage" sgraph_ai_service_playwright__api_site/` returns hits **only** in `shared/api-client.js` and `shared/components/sg-auth-panel.js`.
3. Both `/admin/` and `/user/` load without console errors against a fresh backend.
4. Pasting an invalid API key shows an auth error and does not crash.
5. Starting a Linux stack from `/user/` shows a progress bar that advances against real health-check ticks, and shows READY with public IP after ~60s.
6. Stopping a stack from `/admin/` removes it from the active list within one polling cycle.
7. Adding a sixth stack type would require **zero changes** to any UI file other than `shared/catalog.js` (and only because that file is the in-memory cache key) — adding a type is a server-side catalog entry.

If any of these fails, the UI is not done.
