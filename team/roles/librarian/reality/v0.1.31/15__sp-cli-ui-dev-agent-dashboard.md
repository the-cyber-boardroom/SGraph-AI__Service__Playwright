# Reality — SP CLI Admin Dashboard v2 (dev-agent session) — Slice 15

**Added:** 2026-04-29  
**Branch:** `claude/setup-dev-agent-ui-titBw`  
**Picks up from:** Slice 14 (sg-layout + VNC wiring)

---

## Summary of changes

Six development PRs replaced the polling-based flat admin UI with a fully component-driven
dashboard. The vault-gate, 3-column sg-layout, settings persistence, per-plugin launch
flow, and per-plugin detail panels are all live.

---

## Shared utilities — additions and changes

### `api_site/shared/settings-bus.js` (NEW)

Module-level singleton. Call `startSettingsBus()` once from the page controller.

| Export | Description |
|--------|-------------|
| `startSettingsBus()` | Registers `vault:connected` / `vault:disconnected` listeners |
| `isLoaded()` | Returns true after first vault read completes |
| `getPluginEnabled(name)` | Per-plugin enabled flag (default from `DEFAULTS`) |
| `getAllPluginToggles()` | Deep-clone of `_state.plugins` |
| `getUIPanelVisible(panel)` | Per-panel visible flag |
| `getAllDefaults()` | Deep-clone of `_state.defaults` |
| `setPluginEnabled(name, enabled)` | Mutates + persists; fires `sp-cli:plugin.toggled` |
| `setUIPanelVisible(panel, visible)` | Mutates + persists; fires `sp-cli:ui-panel.toggled` |
| `setDefault(key, value)` | Mutates + persists |

**Vault path:** `sp-cli/preferences.json`  
**Schema:** `{ schema_version: 2, plugins: {...}, ui_panels: {...}, defaults: {...} }`  
**Migration:** v1→v2 handled in `_migrate()` (maps old flat fields to nested shape)  
**Read-only vault:** `_persist()` dispatches `sg-toast` warning instead of writing

Default plugin enablement: `linux=true`, `docker=true`, `elastic=true`, `vnc=true`,
`prometheus=false`, `opensearch=false`, `neko=false`.

---

## Admin dashboard — complete rewrite

**File:** `api_site/admin/admin.js`

### Layout

3-column sg-layout saved to `localStorage` key `sp-cli:admin:root-layout:v1`:

```
row [0.07 / 0.78 / 0.15]
  stack [ sp-cli-left-nav ]
  stack [ sp-cli-compute-view ]           ← main column; tabs added dynamically
  column [ right panels per settings ]    ← only visible panels included
```

The right column is built dynamically via `_buildRootLayout()` which calls
`getUIPanelVisible(key)` for each of the 4 right-column panels. Layout init is
triggered by `sp-cli:settings.loaded` (not `vault:connected`) to avoid the async
race between admin.js and settings-bus both listening to `vault:connected`.

### Event wiring

| Event | Handler |
|-------|---------|
| `vault:connected` | `_setGate(true)` → `_loadData()` |
| `vault:disconnected` | `_setGate(false)` |
| `sp-cli:settings.loaded` | `_initLayout()` (once) |
| `sp-cli:nav.selected` | `_switchView(view)` |
| `sp-cli:stack.selected` / `sp-cli:stack-selected` | `_openDetailTab(stack)` |
| `sp-cli:stack.deleted` / `sp-cli:stack-deleted` | `_onStackDeleted(stack)` |
| `sp-cli:stacks.refresh` / `sp-cli:stacks-refresh` | `_loadData()` |
| `sp-cli:region-changed` | store `_region`, `_loadData()` |
| `sp-cli:plugin.toggled` (enabled=false) | close detail + launch tabs for that type |
| `sp-cli:ui-panel.toggled` (visible=false) | `removePanel(_rightPanelTabIds[panel])` |
| `sp-cli:ui-panel.toggled` (visible=true) | `sg-toast` "Reset Layout to show panel" |
| `sp-cli:plugin:{name}.launch-requested` | `_openLaunchTab(entry)` (7 types) |
| `sp-cli:catalog-launch` / `sp-cli:user-launch` | `_openLaunchTab(entry)` (compat) |
| `sp-cli:launch.success` | close launch tab + activity log + `_loadData()` after 3s |
| `sp-cli:launch.error` | activity log |
| `sp-cli:launch.cancelled` | close launch tab |
| `sp-cli:launch-success` / `sp-cli:launch-error` | compat aliases |
| `sp-cli:stack.stop-requested` | `DELETE /{type}/stack/{name}` → fire `sp-cli:stack.deleted` |
| `sg-auth-saved` | `_loadData()` |

### Tab tracking maps

| Variable | Key → Value |
|----------|-------------|
| `_detailTabIds` | `stack_name → panelId` |
| `_detailTypeIds` | `stack_name → type_id` |
| `_launchTabIds` | `type_id → panelId` |
| `_rightPanelTabIds` | `panel_key → panelId` (populated by `_findRightPanelTabIds(tree)`) |

---

## sp-cli Web Components — new and updated

### Left nav + view stubs

| Component | Path | Role |
|-----------|------|------|
| `sp-cli-left-nav` | `components/sp-cli/sp-cli-left-nav/v0/v0.1/v0.1.0/` | Nav menu; emits `sp-cli:nav.selected { view }` |
| `sp-cli-compute-view` | `components/sp-cli/sp-cli-compute-view/v0/v0.1/v0.1.0/` | Flex-column: launcher-pane (top) + stacks-pane (fill); `setData({ stacks })` forwards to stacks-pane |
| `sp-cli-storage-view` | `components/sp-cli/sp-cli-storage-view/v0/v0.1/v0.1.0/` | Stub |
| `sp-cli-settings-view` | `components/sp-cli/sp-cli-settings-view/v0/v0.1/v0.1.0/` | Full settings panel; reads/writes settings-bus; Reset Layout button |
| `sp-cli-diagnostics-view` | `components/sp-cli/sp-cli-diagnostics-view/v0/v0.1/v0.1.0/` | Stub |

### Right-column panels

| Component | Path | Role |
|-----------|------|------|
| `sp-cli-events-log` | `components/sp-cli/sp-cli-events-log/v0/v0.1/v0.1.0/` | DOM-event trace; 5-family filter (all/vault/stacks/launch/nav); max 300 entries |
| `sp-cli-vault-status` | `components/sp-cli/sp-cli-vault-status/v0/v0.1/v0.1.0/` | Vault connection details; Browse button |
| `sp-cli-active-sessions` | `components/sp-cli/sp-cli-active-sessions/v0/v0.1/v0.1.0/` | Session uptime ticker; multi-user tracking deferred |
| `sp-cli-cost-tracker` | `components/sp-cli/sp-cli-cost-tracker/v0/v0.1/v0.1.0/` | Running-stack cost estimate; `setStacks(stacks)` |

### `_shared/` widgets

| Component | Path | API |
|-----------|------|-----|
| `sp-cli-status-chip` | `_shared/sp-cli-status-chip/` | `setState(state)` → coloured dot + label |
| `sp-cli-stack-header` | `_shared/sp-cli-stack-header/` | `setStack(stack)` → icon + name + status-chip + uptime (10s interval) |
| `sp-cli-stop-button` | `_shared/sp-cli-stop-button/` | `setStack(stack)` → confirm-then-fire `sp-cli:stack.stop-requested { stack }` |
| `sp-cli-ssm-command` | `_shared/sp-cli-ssm-command/` | `setStack(stack)` → builds `aws ssm start-session` command; copy button |
| `sp-cli-network-info` | `_shared/sp-cli-network-info/` | `setStack(stack)` → public_ip, allowed_ip, sg info |
| `sp-cli-launch-form` | `_shared/sp-cli-launch-form/` | `populate(entry, defaults)`, `getValues()`, `reset()`, `setDisabled(disabled)` |
| `sg-remote-browser` | `_shared/sg-remote-browser/` | `open({ url, auth, provider, stackName })` — VNC/iframe/neko/auto providers |

### Plugin cards (`api_site/plugins/`)

7 cards, one per plugin type. Each follows the `SgComponent` 3-file pattern.

| Card element | type_id | POST endpoint | stability | soon |
|---|---|---|---|---|
| `sp-cli-linux-card` | linux | `/linux/stack` | stable | false |
| `sp-cli-docker-card` | docker | `/docker/stack` | stable | false |
| `sp-cli-elastic-card` | elastic | `/elastic/stack` | stable | false |
| `sp-cli-vnc-card` | vnc | `/vnc/stack` | stable | false |
| `sp-cli-prometheus-card` | prometheus | `/prometheus/stack` | experimental | false |
| `sp-cli-opensearch-card` | opensearch | `/opensearch/stack` | experimental | false |
| `sp-cli-neko-card` | neko | `/neko/stack` | experimental | **true** (Launch disabled) |

Clicking Launch fires `sp-cli:plugin:{type_id}.launch-requested { entry }` on `document`.

### Launcher pane + launch panel

| Component | Role |
|-----------|------|
| `sp-cli-launcher-pane` | Reads enabled plugins from `getAllPluginToggles()`; renders enabled cards in a collapsible grid; updates on `sp-cli:settings.loaded` and `sp-cli:plugin.toggled` |
| `sp-cli-launch-panel` | Tab panel (not a modal); wraps `sp-cli-launch-form`; `open(entry)` populates form + auto-generates stack name `{type_id}-{word}-{4digits}`; POSTs to `entry.create_endpoint_path`; fires `sp-cli:launch.success`, `sp-cli:launch.error`, `sp-cli:launch.cancelled` |

### Per-plugin detail panels

All embed `sp-cli-stack-header` + `sp-cli-ssm-command` + `sp-cli-network-info` +
`sp-cli-stop-button`. `open(stack)` fetches `GET /{type}/stack/{name}` and merges
info into widgets.

| Element | Type-specific addition |
|---------|----------------------|
| `sp-cli-linux-detail` | — (common widgets only) |
| `sp-cli-docker-detail` | — (common widgets only) |
| `sp-cli-elastic-detail` | Kibana `:5601` + Elasticsearch `:9200` URLs (shown when running) |
| `sp-cli-vnc-detail` | `sg-remote-browser` in VNC mode embedded when running (port `:6080`) |
| `sp-cli-prometheus-detail` | Grafana `:3000` + Prometheus `:9090` URLs (shown when running) |
| `sp-cli-opensearch-detail` | Dashboards `:5601` + OpenSearch `:9200` URLs (shown when running) |
| `sp-cli-neko-detail` | Stub — "WebRTC not yet supported" |

### `sp-cli-stacks-pane` — updated

Now emits both dotted (`sp-cli:stack.selected`, `sp-cli:stacks.refresh`) and legacy
hyphenated names (`sp-cli:stack-selected`, `sp-cli:stacks-refresh`) for compatibility.

### `sp-cli-vault-picker` — updated

Added `_isConnected` flag. `_toggle()` returns early when connected (prevents panel
opening when vault is already live). `_onConnected()` calls `_close()` to dismiss the
connection panel after a successful connect.

---

## CI change

`build-and-push-image` job condition changed from requiring
`detect-changes.outputs.image-rebuild-needed == 'true'` to
`needs.check-aws-credentials.outputs.has-credentials == 'true'` — always rebuilds the
Docker image on CI. Workaround for a known bug where the dynamic source reload in
Lambda does not pick up API site changes without a full image rebuild.

---

## Deprecated (files exist but no longer referenced in `admin/index.html`)

| Component | Replacement |
|-----------|-------------|
| `sp-cli-stack-detail` | `sp-cli-{type_id}-detail` (per-plugin) |
| `sp-cli-launch-modal` | `sp-cli-launch-panel` |

---

## Not included (PROPOSED — does not exist yet)

- `Routes__OpenSearch__Stack` not mounted on `Fast_API__SP__CLI`
- `Routes__Prometheus__Stack` not mounted on `Fast_API__SP__CLI`
- User provisioning page (`api_site/user/`) not updated to use sg-layout
- Dynamic re-add of right-column panels after toggling visible=true mid-session
  (requires page reload or "Reset Layout" in Settings)
- Playwright/pytest end-to-end UI smoke tests
- Per-instance multi-user session tracking in `sp-cli-active-sessions`
