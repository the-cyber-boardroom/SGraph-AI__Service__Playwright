# 01 — Plugin manifest loader

## Goal

Replace the four hard-coded plugin lists in the dashboard with a single fetch of `/catalog/manifest`, so adding a new plugin requires zero core-file edits — just a `plugins/{name}/` folder and the matching backend registry entry.

## Today

The same plugin list is duplicated in four UI sites:

| File:line | What it stores |
|-----------|----------------|
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-launcher-pane/v0/v0.1/v0.1.0/sp-cli-launcher-pane.js:4` | `PLUGIN_ORDER = ['docker','podman','elastic','vnc','prometheus','opensearch','neko','firefox']` |
| `sgraph_ai_service_playwright__api_site/admin/admin.js:126` | `LAUNCH_TYPES = [...]` (parallel list to wire `sp-cli:plugin:{name}.launch-requested` listeners) |
| `sgraph_ai_service_playwright__api_site/shared/settings-bus.js:11-20` | `DEFAULTS.plugins` — same eight names |
| `sgraph_ai_service_playwright__api_site/admin/index.html:30-67` | One `<script type="module">` per card and per detail file, hand-listed |

`sp-cli-launcher-pane.js:25-39` already filters by toggles but iterates `PLUGIN_ORDER` rather than catalog data. Card metadata (display name, icon, stability, boot, create endpoint) duplicates the same fields each card declares in `STATIC = {...}`. Adding `firefox` and `podman` recently required four parallel edits.

## Required output

A single `shared/plugin-manifest.js` module that:

1. Fetches `/catalog/manifest` once on dashboard boot (after `vault:connected` if the manifest is auth-scoped — currently planned anonymous; see backend brief).
2. Caches the response in memory and exposes:
   - `getManifest()` — returns the cached `Schema__Plugin__Manifest`.
   - `getEntry(type_id)` — returns one `Schema__Plugin__Manifest__Entry`.
   - `getOrder()` — returns the plugin id list (replaces `PLUGIN_ORDER`).
   - `getCapabilities(type_id)` — returns the capability set.
3. Emits `sp-cli:manifest.loaded` once, and `sp-cli:manifest.error` on failure.

Refactors that follow:

- `sp-cli-launcher-pane.js` iterates `getOrder()` and reads card metadata from the manifest entry, not from `STATIC` blobs duplicated per card.
- `admin.js` LAUNCH_TYPES becomes a generated map from `getOrder()`; the listener-wiring loop reads the same map.
- `settings-bus.js` `DEFAULTS.plugins` is computed at first load by walking `getManifest().plugins` and defaulting every entry to `{ enabled: true }` (or per-plugin defaults if the manifest carries them).
- `admin/index.html` keeps the `<script>` tags for cards and details (no build step), but a comment block above the listing references the manifest as the source of truth and warns that adding a script tag without a manifest entry is an error.

## Contract — events the loader emits / consumes

- Emits `sp-cli:manifest.loaded` with `{ entries: [...] }` payload.
- Emits `sp-cli:manifest.error` with `{ error_code, message }` on failure.
- Consumers (`sp-cli-launcher-pane`, `sp-cli-settings-view`) listen and re-render on `manifest.loaded`.

## Acceptance criteria

- All four duplication sites removed (or reduced to a single in-line comment pointing at `plugin-manifest.js`).
- `sp-cli-launcher-pane` renders the same eight cards as today by reading from the manifest, not `PLUGIN_ORDER`.
- Adding a new plugin (a hypothetical `chrome` for the test) requires: (a) backend registry entry → manifest auto-updates, (b) new `plugins/chrome/...` folder and `sp-cli-chrome-detail/...` folder, (c) one new `<script type="module">` line in `admin/index.html`. No edits to the controller, the launcher pane, or settings-bus.
- A unit test asserts that the manifest loader produces a non-empty entry list when the network response matches `Schema__Plugin__Manifest`.
- Settings view "no manifest" state shows a clear error and a retry button (uses `manifest.error`).
- Reality doc UI fragment updated.

## Open questions

1. **Where do per-card visuals live?** Today each card has a `.css` file with its own colour token and an emoji icon. With manifest-driven discovery, should the icon come from the manifest entry (`icon: '🦊'`) or stay in the card module? Recommendation: manifest carries the icon, card module carries the layout — single source for "what plugin is this", per-component for "how does it look".
2. **`stability` consumption.** Manifest carries `stability: stable | experimental | deprecated`. UI today renders a badge on `firefox` (`experimental`). Confirm the visual rules for the closed set.
3. **`soon` flag.** Manifest carries it; UI hides launch button when true. Confirm.
4. **Failure mode.** If `/catalog/manifest` errors, do we fall back to a baked-in last-known list or fail closed? Recommendation: fail closed with a banner — the dashboard is admin-internal, baked-in data goes stale.

## Out of scope

- Loading plugin code from external URLs (a v2 manifest extension). Today the `<script>` tags remain manually listed.
- Server-side per-deployment-target capability filtering. Manifest exposes the union; UI filters with capability hints later.

## Paired-with

- Backend contract: `../v0.1.140__post-fractal-ui__backend/01__plugin-manifest-endpoint.md`.
- Blocked by: backend item 01 must land first.
