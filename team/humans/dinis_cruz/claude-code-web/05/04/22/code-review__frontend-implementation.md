# Frontend Code Review — SG/Compute Dashboard

**Date:** 2026-05-04 22:00 UTC
**Branch:** `dev` @ v0.1.171
**Scope:** `sgraph_ai_service_playwright__api_site/` — admin shell, sp-cli web components,
shared bus modules, plugin cards. No code modifications. Read-only review.

---

## 1. Summary

The dashboard is in a structurally healthy state — the three-file Web Component pattern is
applied uniformly, the `SgComponent` base class gives consistent shadow-DOM access (`this.$()`)
and lifecycle (`onReady()`), and module-level singletons (`apiClient`, `settings-bus`) keep
state sane. The new `sp-cli-nodes-view` is the most ambitious component built so far —
a full 6-tab detail panel with iframe-embedded shell and Swagger docs — and it works, but
it is also where most of the technical debt has accumulated.

The terminology label sweep (F1) shipped, and the new `sp-cli:node.*` event names co-exist
with the old `sp-cli:stack.*` and `sp-cli:stack-*` (hyphenated) names through a
deliberate compat shim in `admin.js` and `sp-cli-stacks-pane.js`. F2/F3/F5/F6 have NOT
shipped: hardcoded plugin lists, two competing "active stacks" components, no per-spec UI
co-location, and zero migration of API URLs to `/api/*` (the docstring claim that "nothing
has migrated" is correct — every call still uses legacy `/catalog/*` and `/{type_id}/stack/*`).

The biggest risks are: state-string hardcoded to `'running'` in 6+ sites (will break the
moment the backend returns `'ready'`), four hardcoded plugin lists that must stay in sync
manually, and zero ARIA / explicit keyboard-focus affordances on the new node-detail tabs.

---

## 2. Per-Pattern Findings

| # | Item | Sev | File:line | Recommendation |
|---|------|-----|-----------|----------------|
| 1 | Three-file pattern (`.js` + `.html` + `.css` siblings under `vN/vN.N/vN.N.N/`) | ✅ | All sampled components | Pattern is uniformly applied across all 30+ sp-cli/* and 8 plugins/* dirs |
| 2 | Shadow-DOM `this.$()` accessor used consistently | ✅ | All sampled components | `SgComponent` base provides it; samples (top-bar, launcher, settings, nodes, compute) all use it |
| 3 | `onReady()` lifecycle (vs `connectedCallback()`) | ✅ | All sampled components | Consistent — `SgComponent` from sg-tools runs `onReady` post-shadow-render |
| 4 | Events on `document` with `{ bubbles, composed }` | ✅ | admin.js:64-167, nodes-view:73-86 | Followed everywhere; legacy `this.emit()` helper does the same |
| 5 | State (`this._foo`) without underscore-private — convention says no underscore prefix | ⚠ | nodes-view:31-71, host-shell:25-32, settings-view:27-31 | CLAUDE.md rule 9 says no underscore prefix for private — JS code violates it consistently. Either drop the rule for JS (it is a Python rule in spirit) or rename. **Recommend: explicitly carve the rule as Python-only in CLAUDE.md** — JS underscore convention is widely understood and refactoring 30+ files for stylistic parity is wasteful. |
| 6 | `apiClient` singleton vs raw `fetch()` to sidecar | ✅ | api-client.js:48 + nodes-view fetch sites | Correct boundary: same-origin SP-CLI backend through `apiClient`; cross-origin sidecar through raw `fetch` (apiClient hardcodes the X-API-Key header which is wrong for sidecar) |
| 7 | Sidecar URL fallback duplicated 6+ times | ⚠ | nodes-view:224, 281, 305, 342, 405, 449, 599; host-shell:50; host-api-panel:20 | `stack.host_api_url \|\| (stack.public_ip ? \`http://${stack.public_ip}:19009\` : '')` is copy-pasted. Extract to `_resolveSidecarUrl(stack)` helper or add to a shared module. |
| 8 | `dispatchEvent(new CustomEvent(...))` boilerplate also duplicated | ⚠ | admin.js:156-166, 263, 279; nodes-view:73, 86, 277 | Some components use `this.emit()` helper from `SgComponent`; admin.js (not a component) and nodes-view both manually construct CustomEvents. Add a top-level `dispatch(name, detail)` to api-client or settings-bus. |
| 9 | Inline HTML via `innerHTML` with handcoded escape (`_esc`) | ⚠ | nodes-view:21, events-log:124, settings-view:95 | `_esc` is redefined in every file. Promote to `shared/escape.js`. Existing pattern is at least safe (escapes `&<>`); just deduplicate. |
| 10 | Pending-state cache (`this._pendingStacks`) for early `setX` before `onReady` | ✅ | nodes-view:81-88, stacks-pane:47, host-shell:45, host-api-panel:15 | Defensive but consistent — good. |
| 11 | Two iframe widgets (`sp-cli-host-shell`, `sp-cli-host-api-panel`) with similar pattern | ⚠ | both files | Could share a `_BaseSidecarFrame` mixin: both compute the URL the same way and both gate-show an "unavailable" panel. Low priority. |
| 12 | Per-plugin detail components (`sp-cli-{type}-detail`) — 8 near-identical files | ⚠ | components/sp-cli/sp-cli-{type}-detail/* | Each is mostly `apiClient.get(\`/{type}/stack/{name}\`)` then renders a kv block. F6 (per-spec UI co-location) is supposed to fix this, but the 8 dispatch sites are still hand-listed in `admin/index.html` script tags and admin.js LAUNCH_TYPES. |
| 13 | `setData(_) {}` no-op stub on `sp-cli-compute-view` | ⚠ | compute-view.js:85 | Confusingly named — admin.js still calls it. Either remove the call site or document why the no-op exists. |
| 14 | Legacy `sp-cli-user-pane` still emits hyphenated `sp-cli:stack-selected` | 🔴 | sp-cli-user-pane.js:92 | Not in the events-log `FAMILIES` map and has no listener anywhere — DEAD event. Remove or migrate. |
| 15 | `sp-cli-catalog-pane` emits `sp-cli:catalog-launch` (hyphenated, compat-only) | ⚠ | sp-cli-catalog-pane.js:50 | admin.js:104 still listens "compat" but no production code path triggers it. Candidate for removal. |
| 16 | `loadCatalog()` cache exists but is never used | ⚠ | shared/catalog.js | admin.js calls `apiClient.get('/catalog/types')` directly, bypassing the cache. Either delete `catalog.js` or wire admin to it. |
| 17 | `sp-cli-launch-form` does external `fetch('https://api.ipify.org/...')` | 🔴 | sp-cli-launch-form.js:95 | Calls a third-party IP-resolution service. Privacy + supply-chain concern. Move to backend or remove. |

---

## 3. Hardcoded Data Inventory (F5 work)

| Location | Constant | What it lists | Removal target |
|----------|----------|---------------|----------------|
| `admin/admin.js:100` | `LAUNCH_TYPES` | All 8 plugin type ids | Drive from `/api/specs` |
| `admin/admin.js:27` | `VIEW_TITLES` | Tab title strings | Move to view components themselves |
| `admin/admin.js:301-304, 315-318` | `viewTags` (duplicated x2) | All view component tags | Compute from layout tree |
| `admin/index.html:32-49, 62-69` | `<script>` tags | Per-plugin card + detail components | F6 — plugin manifest |
| `components/sp-cli/sp-cli-launcher-pane.js:4` | `PLUGIN_ORDER` | All 8 plugin ids in display order | Drive from `/api/specs` (with `display_order` field) |
| `components/sp-cli/sp-cli-compute-view.js:7-16` | `CATALOG` | Full spec metadata (type_id, icon, boot, stability, endpoint path, description) | Replace with `apiClient.get('/api/specs')` once B4 ships |
| `components/sp-cli/sp-cli-compute-view.js:18-20` | `REGIONS`, `INSTANCE_TYPES`, `MAX_HOURS` | AWS choice lists | Move to `shared/aws-options.js` (DRY with settings-view) |
| `components/sp-cli/sp-cli-compute-view.js:22-25` | `NAME_WORDS` | Stack-name word list | Acceptable as static; low priority |
| `components/sp-cli/sp-cli-compute-view.js:34-37` | `COST_TABLE` | Per-instance hourly USD | Move to backend `/api/instance-types` |
| `components/sp-cli/sp-cli-nodes-view.js:9-12` | `TYPE_ICONS` | Per-spec emoji icon | Replace with `spec.icon` from API response |
| `components/sp-cli/sp-cli-nodes-view.js:369` | `LABELS` (port → service) | Per-port display label | Move into spec metadata (B4) |
| `components/sp-cli/sp-cli-events-log.js:14-28, 30-55` | `FAMILIES`, `ICONS` | Full event vocabulary | Acceptable to stay in dashboard (it IS the dashboard's responsibility) — but must be kept in sync with emitter sites |
| `components/sp-cli/_shared/sp-cli-host-shell.js:6-16` | `QUICK_COMMANDS` | 9 dev convenience commands | Acceptable static — could move to sidecar config |
| `components/sp-cli/sp-cli-settings-view.js:9-18` | `UI_PANELS`, `REGIONS`, `INSTANCE_TYPES`, `MAX_HOURS` | Duplicated from compute-view | Consolidate with compute-view (DRY) |
| `shared/settings-bus.js:8-31` | `DEFAULTS.plugins` | Per-plugin enabled boolean (8 entries) | Drive from `/api/specs`, default-enable `stable` ones |

**Headline:** `PLUGIN_ORDER`, `LAUNCH_TYPES`, `DEFAULTS.plugins`, `CATALOG`, `TYPE_ICONS`, the
`<script>` tags in `index.html`, and `default_instance_types` in the v1 settings migration
all hardcode the same set of 8 plugin names. F5 needs to remove ALL of them.

---

## 4. API Call Inventory

Every URL the dashboard hits, grouped by surface. Every one is on the legacy `/catalog/*` or
`/{type_id}/stack/*` namespace — **zero migration to `/api/*` has happened**, confirming the
handover doc.

### SP-CLI backend (same-origin, via `apiClient`)

| Method | Path | Caller | Status |
|--------|------|--------|--------|
| GET | `/catalog/types` | admin.js:257, user.js:76, shared/catalog.js:12 | LEGACY |
| GET | `/catalog/stacks?region=…` | admin.js:258, user.js:77 | LEGACY |
| GET | `/catalog/ec2-info?instance_id=…&region=…` | nodes-view.js:512 | LEGACY |
| POST | `/{type_id}/stack` | compute-view.js:186, launch-panel.js:61, sg-create-modal.js:167 | LEGACY |
| GET | `/{type_id}/stack/{stack_name}` | 7× per-plugin detail components (docker, podman, elastic, vnc, prometheus, opensearch, firefox) | LEGACY |
| GET | `/{type_id}/stack/{stack_name}/health` | sg-create-modal.js:177 | LEGACY |
| DELETE | `/{type_id}/stack/{stack_name}` | admin.js:154 | LEGACY |

### Host sidecar (cross-origin, via raw `fetch` with `X-API-Key`)

| Method | Path | Caller |
|--------|------|--------|
| GET | `{host}/host/status` | nodes-view.js:285, 355 |
| GET | `{host}/host/logs/boot?lines=300` | nodes-view.js:322 |
| POST | `{host}/host/shell/execute` | host-shell.js:91 |
| iframe | `{host}/host/shell/page` | host-shell.js:62 |
| iframe | `{host}/auth/set-cookie-form` | host-shell.js:72 |
| iframe | `{host}/docs-auth?apikey=…` (fallback `/docs`) | host-api-panel.js:38-39 |
| GET | `{host}/pods/list` | nodes-view.js:354 |
| GET | `{host}/pods/{name}/stats` | nodes-view.js:434 |
| GET | `{host}/pods/{name}/logs?tail=200` | nodes-view.js:458, 603 |

### Third-party

| Method | Path | Caller | Concern |
|--------|------|--------|---------|
| GET | `https://api.ipify.org?format=json` | sp-cli-launch-form.js:95 | 🔴 Third-party data leak — replace with backend endpoint. |

---

## 5. State / Field-Name Mismatches

### State string `'running'` (the handover concern)

`sp-cli-nodes-view.js` checks `state === 'running'` in **6 places**:

| Line | Context |
|------|---------|
| 98 | `wasRunning = this._currentStack.state === 'running'` |
| 106 | transition guard `!wasRunning && updated.state === 'running'` |
| 129 | row CSS class — `'running'`/`'stopped'`/else |
| 250 | auto-pick `bootlog` tab if `state !== 'running'` |
| 254 | start health-poll interval if `state !== 'running'` |
| 276, 310 | early-return guards for non-running |

`sp-cli-stacks-pane.js:23-28` separately defines `_stateClass()` that handles
`'running'` / `'stopped'` / `'terminated'` (and treats anything else as `'pending'`).

If `Schema__Node__Info` returns `'ready'` or `'starting'` or `'pending'`, the nodes-view
will: (a) never stop the boot-log poll, (b) never auto-switch off the boot-log tab,
(c) classify the node as "warn" forever. **This is a latent bug.**

**Recommend:** introduce a `shared/node-state.js` module exporting `isRunning(node)`,
`stateClass(node)`, and a typed `NODE_STATE` enum mirror. Use it everywhere.

### Field names — `stack_name` / `type_id` are still universal

Searching the codebase: **0 hits** for `node_id`, `spec_id`, `pod_count`. The frontend
exclusively uses `stack_name` and `type_id`. The only "new" terminology adopted is
`pods` (replacing `containers`) which appears in `nodes-view.js` (the variable, the
sidecar URL `/pods/list`, the loop variable, etc.) — but the EVENT and detail field
names are still `stack_name` / `type_id`.

**Risk:** if the backend's `Schema__Node__Info` rename to `node_id` / `spec_id` ever ships,
**every consumer** breaks. There are 80+ references. F2 (or whichever phase owns the rename)
needs a single rebroadcast in `admin.js._populatePanes()` to bridge during transition.

---

## 6. Event Vocabulary Table

| Event | Emitter | Listener | Status |
|-------|---------|----------|--------|
| `sp-cli:nav.selected` | top-bar:41, left-nav:31 | admin.js:56 | ACTIVE |
| `sp-cli:region-changed` | region-picker:63 | admin.js:73 | ACTIVE |
| `sp-cli:settings.loaded` | settings-bus:50 | admin.js:50, launcher-pane:19, settings-view:43, compute-view:79 | ACTIVE |
| `sp-cli:settings.saved` | settings-bus:88 | events-log only | ACTIVE (telemetry) |
| `sp-cli:plugin.toggled` | settings-bus:67 | admin.js:77, launcher-pane:20 | ACTIVE |
| `sp-cli:ui-panel.toggled` | settings-bus:74 | (none) | RESERVED — emitted but not consumed |
| `sp-cli:node.selected` | stacks-pane:81 | admin.js:64 | ACTIVE |
| `sp-cli:node.deleted` | (none — only listened) | admin.js:65 | RESERVED — listener exists but no emitter |
| `sp-cli:node.launched` | compute-view:187, launch-panel:64 | admin.js:107 | ACTIVE |
| `sp-cli:nodes.refresh` | nodes-view:277, stacks-pane:42 | admin.js:66 | ACTIVE |
| `sp-cli:stack.selected` | (none) | admin.js:67 | DEPRECATED — no live emitter |
| `sp-cli:stack-selected` (hyphen) | user-pane:92, stacks-pane:83 | admin.js:68 | DEPRECATED |
| `sp-cli:stack.deleted` | admin.js:156 (re-broadcast) | admin.js:69, events-log | DEPRECATED — admin still emits it on delete-success |
| `sp-cli:stack-deleted` (hyphen) | (none) | admin.js:70 | DEPRECATED |
| `sp-cli:stacks.refresh` | nodes-view:73, 86, stacks-pane:43 | admin.js:71 | DEPRECATED — but nodes-view (current code) still emits it |
| `sp-cli:stacks-refresh` (hyphen) | stacks-pane:44 | admin.js:72 | DEPRECATED |
| `sp-cli:stacks.updated` | admin.js:279 | cost-tracker:25 | ACTIVE |
| `sp-cli:stack.stop-requested` | stop-button:48 | admin.js:150 | ACTIVE (legacy name; should be `node.stop-requested`) |
| `sp-cli:stack.stop-failed` | admin.js:162 | (none) | RESERVED |
| `sp-cli:launch.success` | compute-view:191, launch-panel:65 | admin.js:117 | DEPRECATED (kept emitting "for compat") |
| `sp-cli:launch-success` (hyphen) | (none) | admin.js:127 | DEPRECATED |
| `sp-cli:launch.error` | launch-panel:69 | admin.js:133 | ACTIVE |
| `sp-cli:launch-error` (hyphen) | (none) | admin.js:136 | DEPRECATED |
| `sp-cli:launch.cancelled` | launch-panel:38 | admin.js:140 | ACTIVE |
| `sp-cli:plugin:{type}.launch-requested` (per-plugin) | each card | admin.js:101-103 | ACTIVE |
| `sp-cli:catalog-launch` | catalog-pane:50 | admin.js:104 | DEPRECATED |
| `sp-cli:user-launch` | user-pane:68 | admin.js:105 | DEPRECATED |
| `sp-cli:activity-entry` | admin.js:285 | activity-pane:24, events-log | ACTIVE |
| `sp-cli:vault-bus:*` (10 events) | vault-bus | events-log only | ACTIVE (telemetry) |
| `sp-cli:vault-picker-opened` / `vault-connected` / `vault-disconnected` | vault-picker | (none in admin) | ACTIVE in vault-status only |
| `sp-cli:brand-clicked` | top-bar:37 | (none) | RESERVED |
| `sg-auth-required` | api-client:33 | admin.js:264 (via `sg-show-auth`) | ACTIVE |
| `sg-auth-saved` | (auth panel) | admin.js:96 | ACTIVE |

### Comparison vs `FAMILIES` map in events-log

The `FAMILIES` map covers most events but **misses**:
- `sp-cli:ui-panel.toggled`
- `sp-cli:stacks.updated`
- `sp-cli:stack.stop-requested`, `sp-cli:stack.stop-failed`
- `sp-cli:launch.cancelled`
- `sp-cli:plugin:{type}.launch-requested` (per-plugin family — by design, but it means launches from cards aren't logged)
- `sp-cli:brand-clicked`
- `sg-auth-required`, `sg-auth-saved`

Recommend either expanding `FAMILIES` or doing a wildcard listener.

---

## 7. Security / Accessibility Quick-Flags

### Security

| Sev | Item |
|-----|------|
| 🔴 | `sp-cli-launch-form` calls `https://api.ipify.org` to resolve caller IP — third-party data leak. Move to backend. |
| ⚠ | `host-api-panel` passes API key in URL query string `?apikey=…` — appears in browser history, referer, server logs. Cookie-based auth (already supported by sidecar) is preferable; the comment says fall-back is `/docs` (no auth) which means a deployed-but-broken sidecar shows authenticated docs as plain unauthenticated. |
| ⚠ | `host-shell` `_openAuth()` loads `/auth/set-cookie-form` inside the SAME iframe — relies on the sidecar's `samesite=lax` cookie behaviour and only works because the iframe is same-origin to the sidecar. Cross-origin iframe + lax cookie = no cookie sent on initial load → confusing UX. Test: open the panel cold; the first POST to `/host/shell/execute` will return 401, requiring a manual `Authenticate` click. The component handles 401 (line 96-99) but doesn't auto-recover. |
| ⚠ | `apiClient` adds `X-API-Key` to every request including cross-origin sidecar calls IF a code path ever uses it for that — currently it doesn't, but the boundary is fragile. |
| ✅ | All `innerHTML` writes go through a `_esc()` HTML-escape function. Verified for nodes-view, events-log, settings-view, stacks-pane. |
| ✅ | No `eval()`, `Function()` constructors, or arbitrary code execution paths in the dashboard JS. |

### Accessibility

Spot-checked **top-bar**, **launcher-pane**, **nodes-view** detail tabs:

| Sev | Item |
|-----|------|
| 🔴 | Zero `aria-*` attributes in any sp-cli component HTML except `sp-cli-left-nav`. The new node-detail tabs (`<button class="sgl-tab" data-tab="overview">`) lack `role="tab"`, `aria-selected`, `aria-controls`. Screen reader cannot announce tab state. |
| 🔴 | Icon-only buttons everywhere lack `aria-label` (only have `title=` attribute, which is inconsistent across browsers/screen readers). Examples: `btn-collapse ◀`, `btn-refresh ↺`, `btn-close-detail ✕`, `api-key-btn 👁`, `api-key-btn ⎘`, `ct-log-btn 📋`, `btn-live-log ▶ Live`. |
| ⚠ | Tab navigation: `.sgl-tab` buttons have no `tabindex` or arrow-key handler. Tab key works (they ARE buttons), but standard tab-pattern keybinding (Left/Right arrows) is absent. |
| ⚠ | `sp-cli-launcher-pane` and `compute-view` cards: `<div class="spec-card">` with click handler — should be `<button>` or have `role="button"` + `tabindex="0"` + Enter/Space handler. As-is, keyboard users cannot launch. |
| ⚠ | Focus visibility — no `:focus-visible` rules in any sampled CSS file. |
| ⚠ | Contrast: emoji icons (🐳🦭🔍🖥📊🌐🦊) are decorative-only and not labelled — aria-hidden missing. |
| ✅ | Plugin-card emojis are explicitly allowed by CLAUDE.md ("plugin card icons stay") so the icon use itself is fine; only the labelling is missing. |

---

## 8. `sp-cli-nodes-view` vs `sp-cli-stacks-pane` — Which is Current?

Both are wired in `admin/index.html` (lines 59 + 64) and both receive data from
`admin.js._populatePanes()` (lines 276 + 277). However:

- The **current main view** (admin.js's `_buildRootLayout()` → "Compute" tab) is
  `sp-cli-compute-view`. From there, navigation to "Active Nodes" via the left-nav
  swaps in `sp-cli-nodes-view`. Only `sp-cli-nodes-view` is reachable through the
  navigation flow.
- `sp-cli-stacks-pane` is only used by `sp-cli-stacks-view` (the older "Stacks"
  legacy view kept for compat) — confirmed via `viewTags` list in admin.js:302.
- `sp-cli-stacks-pane` still emits the **deprecated hyphenated event names**
  (`sp-cli:stack-selected`, `sp-cli:stacks-refresh`) marked "DEPRECATED — remove in F9".
- Feature-set: `sp-cli-nodes-view` has 6-tab detail panel + iframe shell + Swagger docs +
  pod log drawer + EC2 info. `sp-cli-stacks-pane` is a flat list with row-click → emit.

**Verdict:** `sp-cli-nodes-view` is the current path. `sp-cli-stacks-pane` (and its parent
`sp-cli-stacks-view`) are legacy. Once F9 removes the deprecated event names, both can be
deleted along with the `viewTags` reference. **Recommend: delete in v0.2.**

---

## 9. Per-Spec UI Co-Location Audit (F6)

`find sg_compute_specs/ -type d -name ui` returned **0 hits**. `find sg_compute_specs -name '*.js' -o -name '*.html'` also returned **0 hits**. **Confirmed: zero per-spec UI is co-located with backend specs today.** F6 is fully ahead.

---

## 10. Top 5 Things to Tackle in v0.2 Frontend Plan

1. **Drive specs from the API (F4/F5).** Ship `GET /api/specs` and refactor `CATALOG`,
   `PLUGIN_ORDER`, `LAUNCH_TYPES`, `DEFAULTS.plugins`, `TYPE_ICONS`, and the per-plugin
   `<script>` tags in `admin/index.html` to be data-driven. This single change kills
   the four-list sync hazard and unblocks F6.

2. **Centralise node-state vocabulary.** Create `shared/node-state.js` with
   `isRunning(node)`, `stateClass(node)`, and a small enum mirror. Replace the 6 hardcoded
   `state === 'running'` checks in `sp-cli-nodes-view.js` and the bespoke `_stateClass`
   in `sp-cli-stacks-pane.js`. Ship before backend swaps `'running'` for `'ready'`.

3. **Delete legacy event names + legacy components.** Remove the 8 DEPRECATED listeners in
   admin.js, the duplicate `emit` calls in `sp-cli-stacks-pane`, the unused `sp-cli-user-pane`
   handler, and (after F9) `sp-cli-stacks-pane` + `sp-cli-stacks-view` themselves. Also
   delete `shared/catalog.js` (unused) and the third-party `api.ipify.org` call in
   `sp-cli-launch-form`.

4. **Accessibility pass on `sp-cli-nodes-view`.** Add `role="tablist"` + `role="tab"` +
   `aria-selected` + arrow-key navigation to the 6-tab panel; add `aria-label` to every
   icon-only button (`◀ ↺ ✕ 👁 ⎘ 📋 ▶`); replace the click-on-`<div>` spec cards in
   `compute-view` and the plugin cards with real `<button>` elements; add `:focus-visible`
   styles. This is a 200-line, low-risk PR.

5. **Extract sidecar URL + dispatch helpers.** Promote the
   `stack.host_api_url || (stack.public_ip ? \`http://${ip}:19009\` : '')` formula to
   `shared/sidecar.js` (with a `sidecarFetch(stack, path)` helper that also adds the
   `X-API-Key` header). Promote `_esc(s)` to `shared/escape.js`. Promote
   `dispatch(name, detail)` to `shared/events.js`. Each of these is duplicated 5+ times
   today and the duplication is where the hyphen-vs-dot event regression originally crept in.

---

*Reviewer note: no code modified. All findings are reproducible from a clean
`git checkout dev`. Estimated debt removal effort for items 1-5 above: ~3 days
of focused work for one Dev, gated by backend `/api/specs` shipping.*
