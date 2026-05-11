# Brief: sgraph.ai Site Changes for Playwright Screenshot Reliability

**To:** Dev agent (sgraph.ai website)
**From:** Conductor / Infrastructure
**Re:** Site-side changes to make automated screenshot capture reliable
**Version:** v0.2.0 / qa environment
**Date:** 2026-05-08

---

## Background

The `dev.sg-playwright.sgraph.ai` Playwright service is now being used to take automated
screenshots of sgraph.ai pages for documentation, QA, and agent-assisted site management.

The current workaround is `wait_until: "networkidle"` on navigate, which works but is
fragile — it relies on network silence heuristics rather than actual render completion.
The changes below give the Playwright service reliable, deterministic signals that content
has fully loaded.

---

## Change 1 (HIGH PRIORITY) — Add `#content-ready` sentinel element

### What
Add a `<div id="content-ready">` to each page, rendered only after all dynamic content
has been fetched and mounted.

### Where
Any element that is rendered as the final step of the page's JS initialisation. Specifically:
- The element must **not** be present in the initial HTML
- It must be **inserted into the DOM** (or made visible) only after all async data has loaded
- It must be in the `<body>`, not inside a shadow DOM

### Implementation (example)

```javascript
// After all data fetching and component mounting is complete:
const sentinel = document.createElement('div')
sentinel.id = 'content-ready'
sentinel.style.display = 'none'  // invisible, but present in DOM
document.body.appendChild(sentinel)
```

Or, if the site uses a framework with a lifecycle hook:

```javascript
// Vue / React / Svelte — in the equivalent of onMounted / useEffect cleanup
onAllDataLoaded(() => {
  document.body.insertAdjacentHTML('beforeend', '<div id="content-ready" style="display:none"></div>')
})
```

### Why it matters
The Playwright `wait_for` step can then do:
```json
{"action": "wait_for", "selector": "#content-ready", "timeout_ms": 10000}
```
This is a hard, deterministic signal. `networkidle` can misfire on pages with WebSockets,
polling, or lazy-loaded assets. The sentinel cannot.

---

## Change 2 (MEDIUM PRIORITY) — Add `window.__playwright_ready` flag

### What
Set a JS global flag to `false` at page load start, and `true` when fully rendered.

### Implementation

```javascript
// At the very top of your app entry point, before any async work:
window.__playwright_ready = false

// After all data is loaded and DOM is fully rendered:
window.__playwright_ready = true
```

### Why it matters
This enables `wait_for_function` (a new Playwright Service step type being requested — see
Brief 3). The pattern `window.__playwright_ready === true` is a standard Playwright idiom
for exactly this scenario and is widely understood by any agent writing automation scripts.

It also gives the Playwright service a way to confirm render state without relying on
specific CSS selectors (which are more brittle than a simple boolean flag).

---

## Change 3 (LOW PRIORITY) — Add `data-page-id` attribute to `<body>`

### What
Set a `data-page-id` attribute on `<body>` that reflects the current route/section.

### Implementation

```html
<body data-page-id="dev-issues">
```

Or set dynamically on route change:
```javascript
document.body.setAttribute('data-page-id', currentRoute.id)
```

### Why it matters
The Playwright service can then verify it is looking at the correct page before screenshotting:
```json
{"action": "wait_for", "selector": "body[data-page-id='dev-issues']"}
```
This prevents false-positive screenshots when redirects or error pages are served silently.

---

## Current Issues Blocking Screenshot Quality

These are the three open issues on `qa.sgraph.ai/en-gb/dev/issues/` that directly affect
automated screenshot capture:

### I-003 — CRITICAL: Dev section pages failing to load content (IN-PROGRESS)
**Impact on screenshots:** Dev section pages may screenshot as blank or partially rendered
even after `networkidle`. The `#content-ready` sentinel (Change 1 above) will make this
failure visible to the automation rather than silently producing a bad screenshot.
**Dependency:** Change 1 must land before I-003 is considered fully fixed from a QA standpoint.

### I-002 — HIGH: Nav buttons LIBRARY/DEV shift position on selection
**Impact on screenshots:** If screenshots capture transitional states, nav buttons may appear
misaligned. Not blocking for content screenshots but affects visual regression testing.
**Recommendation:** The `wait_for #content-ready` pattern (Change 1) will ensure we screenshot
post-render, avoiding transitional states.

### I-001 — MEDIUM: Footer — minimise legacy content, add deployment version info
**Impact on screenshots:** Low direct impact, but adding the version info to the footer
would let the Playwright service extract it via `get_content` for automated version verification.
**Recommendation:** Include a machine-readable element: `<span id="site-version">v0.2.0</span>`.

---

## Acceptance Criteria

The site changes are complete when the following sequence succeeds without `halt_on_error`
and produces a fully-rendered screenshot:

```json
{
  "steps": [
    {"action": "navigate", "url": "https://qa.sgraph.ai/en-gb/library/", "wait_until": "networkidle"},
    {"action": "wait_for", "selector": "#content-ready", "timeout_ms": 8000},
    {"action": "screenshot", "save_as": "library.png"}
  ]
}
```

All three pages (library, dev/issues, dev/) should pass this sequence.
