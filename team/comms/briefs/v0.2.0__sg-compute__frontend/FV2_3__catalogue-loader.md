# FV2.3 — `shared/spec-catalogue.js` + delete hardcoded plugin lists

## Goal

Code review found **6 hardcoded spec lists** in the dashboard:

- `sp-cli-launcher-pane.js:4` — `PLUGIN_ORDER` (8 entries; missing 4 specs)
- `sp-cli-compute-view.js:6+` — `CATALOG` (8 entries; missing 4 specs)
- `admin.js` — `LAUNCH_TYPES` (parallel list)
- `shared/settings-bus.js:11+` — `DEFAULTS.plugins` (8 entries)
- `shared/catalog.js` — older catalog cache (now legacy)
- `admin/index.html` — `<script>` tags per card / detail (must be hand-synced)

This phase replaces all six with one server-driven catalogue.

## Tasks

1. **Create `shared/spec-catalogue.js`:**
   ```js
   import { apiClient } from './api-client.js'
   
   let cached = null
   
   export async function loadCatalogue() {
       if (cached) return cached
       const response = await apiClient.get('/api/specs')
       cached = response   // { specs: [...] }
       document.dispatchEvent(new CustomEvent('sp-cli:catalogue.loaded',
           { detail: { specs: cached.specs }, bubbles: true, composed: true }))
       return cached
   }
   
   export function getCatalogue() {
       if (!cached) throw new Error('catalogue not loaded; call loadCatalogue() first')
       return cached
   }
   
   export function getSpec(spec_id) {
       return getCatalogue().specs.find(s => s.spec_id === spec_id)
   }
   ```
2. **Boot the catalogue on dashboard load** — call `loadCatalogue()` from `admin/admin.js` startup.
3. **Refactor consumers:**
   - `sp-cli-launcher-pane.js` — delete `PLUGIN_ORDER`; iterate `getCatalogue().specs` filtered by settings-bus toggles.
   - `sp-cli-compute-view.js` — delete `CATALOG`; consume `getCatalogue().specs`.
   - `admin.js` — delete `LAUNCH_TYPES`; build the listener-wiring map from the catalogue.
   - `shared/settings-bus.js` — `DEFAULTS.plugins` becomes empty `{}`; on first load, populate from catalogue (every spec defaults to `enabled: true`).
4. **Delete `shared/catalog.js`** (old cache; superseded). Update any imports.
5. **Document `<script>` tags in `admin/index.html`** — the per-spec card + detail script tags stay (until FV2.6 co-locates UI). Add a header comment: "Until FV2.6, per-spec UI lives here. Manifest is the source of truth for the spec list; if a script tag exists for a spec NOT in the catalogue, the card will not render."
6. **Smoke test** — adding a 13th spec to the backend (edit a manifest's `spec_id`) and reloading the page makes its card appear (assuming the script tag for the card exists; FV2.6 fixes that). For now, the smoke test confirms the catalogue-driven listing works for any spec the backend exposes.
7. Update reality doc / PR description.

## Acceptance criteria

- `shared/spec-catalogue.js` exists; `loadCatalogue()` is called on dashboard boot.
- `sp-cli:catalogue.loaded` event dispatched; observable in events log.
- `PLUGIN_ORDER`, `CATALOG`, `LAUNCH_TYPES`, `DEFAULTS.plugins` all gone (or reduced to empty placeholders).
- `shared/catalog.js` deleted; no remaining imports.
- All 12 specs render cards in the launcher (was 8 before this phase).
- Snapshot tests updated.

## Open questions

- **Catalogue refresh policy.** Cache for the page lifetime, or auto-refresh every N minutes? Recommend page-lifetime cache; refresh on `Spec catalogue → Reload` button (FV2.4).

## Blocks / Blocked by

- **Blocks:** FV2.4 (Specs view consumes the catalogue), FV2.6 (per-spec UI relies on the catalogue's `spec_id`).
- **Blocked by:** FV2.2 (API client migration must be done first).

## Notes

This is the **catalogue-driven discovery** that the v0.1.140 plan promised. After this lands, **adding a new spec on the backend requires zero frontend code change** — the dashboard discovers it.
