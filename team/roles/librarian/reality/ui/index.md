# ui — Reality Index

**Domain:** `ui/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** consolidated from `_archive/v0.1.31/13,14,15__*.md` (slices 13/14/15).

The static-site dashboard served from `sgraph_ai_service_playwright__api_site/`. Three generations layered in three slices:

- **Slice 13** — MVP admin + user pages, polling-based flat layout, original `sg-*` web components and `sp-cli-*` family v0.
- **Slice 14** — sg-layout fractal pane rebuild + VNC wiring.
- **Slice 15** — Six dev-agent PRs replacing the polling admin with vault-gated 3-column sg-layout, settings persistence, per-plugin launch + detail panels.

> **Post-v0.1.31 note:** T3.3b (2026-05-05) renamed `components/sp-cli/` → `components/sg-compute/`. FV2.6 moved per-plugin card + detail components into `sg_compute_specs/{spec}/ui/{card,detail}/` and deleted `api_site/plugins/`. See [`sg-compute/index.md`](../sg-compute/index.md) for the current dashboard component table. The v0.1.31 freeze description below is partially superseded — **VERIFY** against the current `api_site/` tree.

---

## EXISTS (code-verified at v0.1.31; partial-VERIFY since T3.3b/FV2.6)

### Slice 13 — MVP polling UI

#### Shared utilities (`api_site/shared/`)

- `tokens.css` — CSS custom properties (colours, spacing, typography).
- `api-client.js` — module singleton `ApiClient`; reads/writes `sg_api_url` + `sg_api_key` from localStorage; 401 → `sg-auth-required` event.
- `catalog.js` — page-lifetime cache of `/catalog/types`.
- `poll.js` — health-poll loop; 3-phase back-off (3s/5s/10s); visibility-pause; timeout + stopOn support.

#### Web Components (`shared/components/`)

| Component | Role |
|-----------|------|
| `sg-api-client.js` | No-render; listens for `sg-auth-required`, opens auth panel |
| `sg-auth-panel.js` | Connection drawer; API URL + key inputs; shadow DOM |
| `sg-header.js` | Top bar with title slot + settings button |
| `sg-toast-host.js` | Listens for `sg-toast` event; transient toasts |
| `sg-stack-card.js` | One stack; compact / detail modes; stop button |
| `sg-stack-grid.js` | 4 render modes: `admin-table`, `type-cards`, `user-cards`, `user-active` |
| `sg-create-modal.js` | 3-state modal: form → progress → ready |

#### Pages

- `admin/index.html` + `admin.js` + `admin.css` — dashboard shell; type-card strip + active-stacks table; polls `/catalog/stacks` every 30s.
- `user/index.html` + `user.js` + `user.css` — provisioning shell; available-type cards + active stacks; polls active stacks every 15s.
- Root `index.html` — landing page with [Admin Dashboard] / [Provision] nav links.

#### Local dev

- `scripts/ui__serve-locally.sh` — serves `api_site/` via `python3 -m http.server` on port 8090. Pair with `scripts/sp-cli__run-locally.sh` (port 10071).

---

### Slice 14 — sg-layout fractal pane rebuild + VNC wiring

#### UI architecture change

The slice-13 polling/flat layout was replaced by `<sg-layout>` (CDN `https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/`) — a fractal splitter/tab container. Each pane is a custom element using the `SgComponent` 3-file pattern (`.js` + `.html` + `.css`), shadow DOM, `static jsUrl = import.meta.url`.

Vault authentication via:
- `<sg-vault-connect>` (CDN) — credentials form inside the vault-picker dropdown.
- `vault-bus.js` — page-level vault state; `startVaultBus()`, `getRestorablePrefill()`.
- Auto-connect via `_tryAutoConnect()` — clicks the Connect button in `sg-vault-connect`'s shadow DOM when saved credentials exist (`sg-vault:last-key`, `sg-vault:last-api`).

#### sp-cli Web Components (`api_site/components/sp-cli/` — pre-rename)

All follow `SgComponent` base from CDN. All component CSS includes `[hidden] { display: none !important }` to prevent `display: flex/grid` from overriding the `hidden` attribute.

| Component | v | Role |
|-----------|---|------|
| `sp-cli-top-bar` | 0.1.0 | Title slot + region-picker slot + vault-picker slot |
| `sp-cli-region-picker` | 0.1.0 | Region dropdown; emits `sp-cli:region-changed { region }` |
| `sp-cli-vault-picker` | 0.1.0 | Vault dropdown; embeds `<sg-vault-connect>`; "Token settings" button |
| `sp-cli-catalog-pane` | 0.1.0 | `setTypes(entries)` renders type cards with Launch buttons |
| `sp-cli-stacks-pane` | 0.1.0 | `setStacks(stacks)` renders active stack rows |
| `sp-cli-activity-pane` | 0.1.0 | Reverse-chronological log; Clear button |
| `sp-cli-vault-activity` | 0.1.0 | Vault read/write trace |
| `sp-cli-user-pane` | 0.1.0 | Combined pane: available-type cards (top) + active-stacks strip (bottom) |
| `sp-cli-launch-modal` | 0.1.0 | Launch wizard modal; POSTs to `entry.create_endpoint_path` |
| `sp-cli-stack-detail` | 0.1.0 | Right column pane; fetches `GET /{type}/stack/{name}`; Delete with inline confirm |

**Timing guards:** all `set*()` methods buffer their data if the component's `onReady()` has not yet fired.

#### Admin dashboard layout (slice 14)

3-column, persisted to `localStorage` key `sp-cli:admin:layout:v2`:

```
row [
  sp-cli-catalog-pane            (~42%)
  column [
    sp-cli-stacks-pane           (~55% middle column)
    sp-cli-activity-pane         (~45% middle column)
  ]                              (~36%)
  column [
    sp-cli-vault-activity
    sp-cli-stack-detail          ← tabs
  ]                              (~22%)
]
```

#### VNC wiring (slice 14)

- `Fast_API__SP__CLI` gained `vnc_service: Vnc__Service`; mounts `Routes__Vnc__Stack` + `Routes__Vnc__Flows`.
- `Stack__Catalog__Service` gained `vnc_service` field + VNC branch in `list_all_stacks()`.
- 6 VNC routes added: see [`cli/observability.md`](../cli/observability.md).

#### New primitive — `Safe_Str__Endpoint__Path`

`sgraph_ai_service_playwright__cli/catalog/primitives/Safe_Str__Endpoint__Path.py`. `Safe_Str__Text` was converting `/` to `_`, turning `/linux/stack` into `_linux_stack` and breaking UI fetch URLs. Allows lowercase, digits, `/`, `-`, `_`, `{`, `}`.

Schema changes:
- `Schema__Stack__Type__Catalog__Entry.*_endpoint_path` → `Safe_Str__Endpoint__Path`.
- `Schema__Stack__Type__Catalog__Entry.default_max_hours` default → `1`.

---

### Slice 15 — Dev-agent dashboard rewrite (6 PRs)

#### `api_site/shared/settings-bus.js` (NEW)

Module-level singleton. Call `startSettingsBus()` once from the page controller.

Vault path: `sp-cli/preferences.json`. Schema: `{ schema_version: 2, plugins: {...}, ui_panels: {...}, defaults: {...} }`. v1→v2 migration in `_migrate()`. Read-only vault: `_persist()` dispatches `sg-toast` warning instead of writing.

Default plugin enablement: `linux=true`, `docker=true`, `elastic=true`, `vnc=true`, `prometheus=false`, `opensearch=false`, `neko=false`.

#### Admin dashboard — complete rewrite (`api_site/admin/admin.js`)

3-column sg-layout saved to `localStorage` key `sp-cli:admin:root-layout:v1`:

```
row [0.07 / 0.78 / 0.15]
  stack [ sp-cli-left-nav ]
  stack [ sp-cli-compute-view ]
  column [ right panels per settings ]
```

The right column is built dynamically via `_buildRootLayout()` which calls `getUIPanelVisible(key)` for each of the 4 right-column panels. Layout init triggered by `sp-cli:settings.loaded` (not `vault:connected`) to avoid the async race.

#### sp-cli Web Components — new and updated (slice 15)

**Left nav + view stubs:**

| Component | Path | Role |
|-----------|------|------|
| `sp-cli-left-nav` | `components/sp-cli/sp-cli-left-nav/v0/v0.1/v0.1.0/` | Nav menu; emits `sp-cli:nav.selected` |
| `sp-cli-compute-view` | `.../sp-cli-compute-view/...` | Flex-column: launcher-pane (top) + stacks-pane (fill) |
| `sp-cli-storage-view` | `.../sp-cli-storage-view/...` | Stub |
| `sp-cli-settings-view` | `.../sp-cli-settings-view/...` | Full settings panel; Reset Layout button |
| `sp-cli-diagnostics-view` | `.../sp-cli-diagnostics-view/...` | Stub |

**Right-column panels:** `sp-cli-events-log`, `sp-cli-vault-status`, `sp-cli-active-sessions`, `sp-cli-cost-tracker`.

**`_shared/` widgets:** `sp-cli-status-chip`, `sp-cli-stack-header`, `sp-cli-stop-button`, `sp-cli-ssm-command`, `sp-cli-network-info`, `sp-cli-launch-form`, `sg-remote-browser` (VNC/iframe/neko/auto).

**Plugin cards (`api_site/plugins/`) — 7 cards, one per plugin type** (note: this folder was DELETED in FV2.6 — see top-of-file note):

| Card | type_id | POST endpoint | stability | soon |
|------|---------|---------------|-----------|------|
| `sp-cli-linux-card` | linux | `/linux/stack` | stable | false |
| `sp-cli-docker-card` | docker | `/docker/stack` | stable | false |
| `sp-cli-elastic-card` | elastic | `/elastic/stack` | stable | false |
| `sp-cli-vnc-card` | vnc | `/vnc/stack` | stable | false |
| `sp-cli-prometheus-card` | prometheus | `/prometheus/stack` | experimental | false |
| `sp-cli-opensearch-card` | opensearch | `/opensearch/stack` | experimental | false |
| `sp-cli-neko-card` | neko | `/neko/stack` | experimental | **true** (Launch disabled) |

Clicking Launch fires `sp-cli:plugin:{type_id}.launch-requested { entry }` on `document`.

**Launcher pane + launch panel:** `sp-cli-launcher-pane` (renders enabled cards in collapsible grid; updates on `sp-cli:settings.loaded` + `sp-cli:plugin.toggled`); `sp-cli-launch-panel` (tab panel, not modal; wraps `sp-cli-launch-form`; auto-generates stack name `{type_id}-{word}-{4digits}`; fires `launch.success/error/cancelled`).

**Per-plugin detail panels:** all embed `sp-cli-stack-header` + `sp-cli-ssm-command` + `sp-cli-network-info` + `sp-cli-stop-button`. `open(stack)` fetches `GET /{type}/stack/{name}`.

| Element | Type-specific addition |
|---------|------------------------|
| `sp-cli-linux-detail` | — |
| `sp-cli-docker-detail` | — |
| `sp-cli-elastic-detail` | Kibana `:5601` + Elasticsearch `:9200` URLs |
| `sp-cli-vnc-detail` | `sg-remote-browser` in VNC mode (port `:6080`) |
| `sp-cli-prometheus-detail` | Grafana `:3000` + Prometheus `:9090` URLs |
| `sp-cli-opensearch-detail` | Dashboards `:5601` + OpenSearch `:9200` URLs |
| `sp-cli-neko-detail` | Stub — "WebRTC not yet supported" |

**`sp-cli-stacks-pane` updated:** emits both dotted (`sp-cli:stack.selected`, `sp-cli:stacks.refresh`) and legacy hyphenated names for compatibility.

**`sp-cli-vault-picker` updated:** added `_isConnected` flag; `_toggle()` returns early when connected; `_onConnected()` calls `_close()`.

#### Deprecated (files exist but no longer referenced in `admin/index.html`)

| Component | Replacement |
|-----------|-------------|
| `sp-cli-stack-detail` | `sp-cli-{type_id}-detail` (per-plugin) |
| `sp-cli-launch-modal` | `sp-cli-launch-panel` |

---

### CI change (slice 15)

`build-and-push-image` job condition changed from `detect-changes.outputs.image-rebuild-needed == 'true'` to `needs.check-aws-credentials.outputs.has-credentials == 'true'` — always rebuilds the Docker image on CI. Workaround for a known bug where dynamic source reload in Lambda does not pick up API site changes without a full image rebuild.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Sources: [`_archive/v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md`](../_archive/v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md), [`14__sp-cli-ui-sg-layout-vnc-wiring.md`](../_archive/v0.1.31/14__sp-cli-ui-sg-layout-vnc-wiring.md), [`15__sp-cli-ui-dev-agent-dashboard.md`](../_archive/v0.1.31/15__sp-cli-ui-dev-agent-dashboard.md)
- Backend routes consumed: [`cli/observability.md`](../cli/observability.md)
- Settings persistence in vault: [`vault/index.md`](../vault/index.md)
- Current dashboard component table (post T3.3b / FV2.6): [`sg-compute/index.md`](../sg-compute/index.md)
