# ui — Reality Index

**Domain:** `ui/` | **Last updated:** 2026-05-18 | **Maintained by:** Librarian
**Code-source basis:** verified against `sgraph_ai_service_playwright__api_site/` and `sg_compute_specs/*/ui/` at v0.2.28 (post-T3.3b + post-FV2.6).

The static-site dashboard served from `sgraph_ai_service_playwright__api_site/`. The post-rename folder is the current canonical home; the legacy short-form `api_site/` no longer exists.

Three historical slices feed into the current shape:

- **Slice 13** — MVP admin + user pages, polling-based flat layout, original `sg-*` web components.
- **Slice 14** — sg-layout fractal pane rebuild + VNC wiring.
- **Slice 15** — Six dev-agent PRs replacing the polling admin with vault-gated 3-column sg-layout, settings persistence, per-plugin launch + detail panels.

Post-v0.1.31 changes that **superseded** much of the freeze description:

- **T3.3b (2026-05-05):** `components/sp-cli/` → `components/sg-compute/` directory rename; 28 api_site/ string refs + 45 per-spec absolute imports updated; all `sp-cli-*` element names rewritten to `sg-compute-*`.
- **FV2.6 (2026-05-05):** per-plugin card + detail components moved from `api_site/plugins/` into `sg_compute_specs/{spec}/ui/{card,detail}/v0/v0.1/v0.1.0/`. The `api_site/plugins/` folder was deleted. `admin/index.html` now loads them from `/api/specs/<id>/ui/...` via a backend StaticFiles mount.

The slice-13/14/15 freeze sections below are kept for **historical context** only — the current authoritative component inventory is in the table at the bottom of this file (and mirrored in [`sg-compute/index.md`](../sg-compute/index.md)).

---

## EXISTS (code-verified at v0.2.28)

### Current top-level layout (`sgraph_ai_service_playwright__api_site/`)

```
sgraph_ai_service_playwright__api_site/
├── __init__.py
├── index.html                              landing page
├── admin/                                  admin dashboard shell
│   ├── admin.css
│   ├── admin.js                            sg-layout: row[stack(left-nav) | stack(compute-view)]
│   └── index.html                          mounts all sg-compute-* + per-spec card/detail scripts
├── user/                                   user (provisioning) shell
│   ├── index.html
│   ├── user.css
│   └── user.js
├── shared/                                 page-shared utilities + legacy widgets
│   ├── api-client.js                       ApiClient singleton, sg-auth-required event
│   ├── ec2-tokens.css                      EC2-specific CSS custom properties
│   ├── launch-defaults.js
│   ├── node-state.js
│   ├── poll.js                             3-phase back-off polling
│   ├── settings-bus.js                     vault-backed sp-cli/preferences.json (schema_version=2)
│   ├── spec-catalogue.js                   /api/specs/catalogue loader
│   ├── tokens.css                          shared CSS tokens
│   ├── vault-bus.js                        page-level vault state + auto-connect
│   └── components/                         7 legacy sg-* widgets (sg-api-client, sg-auth-panel, sg-create-modal, sg-header, sg-stack-card, sg-stack-grid, sg-toast-host)
└── components/sg-compute/                  current dashboard components (post-T3.3b rename)
```

### `components/sg-compute/` — 23 top-level + `_shared/` (24 entries)

#### Layout / shell components (3)

| Element | Notes |
|---------|-------|
| `sg-compute-top-bar` | Title slot + region-picker slot + vault-picker slot |
| `sg-compute-region-picker` | Region dropdown |
| `sg-compute-vault-picker` | Vault dropdown; embeds `<sg-vault-connect>` |

#### Left nav + view panes (8 — one per top-level nav entry)

| Element | Role |
|---------|------|
| `sg-compute-left-nav` | Nav menu; emits `sp-cli:nav.selected` |
| `sg-compute-compute-view` | Default view — launcher pane (top) + stacks pane (fill) |
| `sg-compute-nodes-view` | Active EC2 nodes table |
| `sg-compute-specs-view` | Browseable spec catalogue |
| `sg-compute-stacks-view` | Active stacks list |
| `sg-compute-storage-view` | Storage browser shell |
| `sg-compute-settings-view` | Full settings panel; Reset Layout button |
| `sg-compute-diagnostics-view` | Wraps the 5 diagnostics panels below |
| `sg-compute-api-view` | Embedded API docs view |

#### Diagnostics panel children (5)

`sg-compute-events-log`, `sg-compute-vault-status`, `sg-compute-active-sessions`, `sg-compute-cost-tracker`, `sg-compute-storage-viewer`.

#### Launch + detail wrappers (3)

`sg-compute-launcher-pane` (renders enabled cards in collapsible grid; updates on `sp-cli:settings.loaded` + `sp-cli:plugin.toggled`), `sg-compute-launch-panel` (tab panel; auto-generates stack name `{type_id}-{word}-{4digits}`; fires `launch.success/error/cancelled`), `sg-compute-spec-detail` (catalogue detail pane).

#### Legacy / lingering panes (3)

`sg-compute-catalog-pane`, `sg-compute-activity-pane`, `sg-compute-user-pane` — retained from the slice-14 user-page; not referenced by `admin/index.html`'s active script tags but kept under the dir.

#### `_shared/` widgets (11)

`sg-compute-ami-picker`, `sg-compute-host-api-panel`, `sg-compute-host-shell`, `sg-compute-images-panel`, `sg-compute-launch-form`, `sg-compute-network-info`, `sg-compute-ssm-command`, `sg-compute-stack-header`, `sg-compute-status-chip`, `sg-compute-stop-button`, `sg-remote-browser` (VNC / iframe / neko / auto).

---

### Per-spec card + detail components — owned by each spec (FV2.6)

Loaded by `admin/index.html` from `/api/specs/<spec_id>/ui/card|detail/v0/v0.1/v0.1.0/sg-compute-<spec_id>-{card,detail}.js` via a backend StaticFiles mount. 8 specs migrated:

| Spec | card | detail | stability | soon |
|------|:----:|:------:|-----------|:----:|
| `docker` | ✅ | ✅ | stable | false |
| `podman` | ✅ | ✅ | stable | false |
| `elastic` | ✅ | ✅ | stable | false |
| `vnc` | ✅ | ✅ | stable | false |
| `prometheus` | ✅ | ✅ | experimental | false |
| `opensearch` | ✅ | ✅ | experimental | false |
| `neko` | ✅ | ✅ | experimental | **true** (Launch disabled — "Coming soon") |
| `firefox` | ✅ | ✅ | (per manifest) | false |

(Source paths e.g. `sg_compute_specs/docker/ui/card/v0/v0.1/v0.1.0/sg-compute-docker-card.js`.)

There is **no `sg_compute_specs/playwright/ui/`** — Playwright is the runtime service, not a UI-dashboard plugin, so it has no card/detail.

---

### Admin layout (`admin/admin.js`)

`ROOT_LAYOUT_KEY = 'sp-cli:admin:root-layout:v3'`. Two-column sg-layout:

```
row [0.07 / 0.93]
  stack [ sg-compute-left-nav    ] (locked)
  stack [ sg-compute-compute-view ] (locked)
```

The diagnostics column (`sg-compute-diagnostics-view`) is rendered as a hidden sibling and revealed via the left nav when the user picks Diagnostics. Per-node host-API-key map is persisted to `localStorage['sp-cli:host-api-keys']`.

`startSettingsBus()` is called at load; catalogue load via `loadCatalogue()`; layout boots immediately (no waiting on vault connect).

---

### Slice freeze sections (historical — superseded by the table above)

The original three-slice description (polling MVP → sg-layout → dev-agent rewrite) and all `sp-cli-*` element names are preserved in the `_archive/v0.1.31/13,14,15__*.md` source briefs. Every `sp-cli-*` element was renamed `sg-compute-*` in T3.3b; the slice-13/14/15 sections of the v0.1.31 freeze should be read with that mechanical rename in mind. The plugin-card folder `api_site/plugins/` was deleted in FV2.6 — its 7 cards now live one-per-spec under `sg_compute_specs/{spec}/ui/`, plus `firefox` was added as an 8th.

---

### Settings persistence (`shared/settings-bus.js`)

Vault path: `sp-cli/preferences.json`. Schema: `{ schema_version: 2, plugins: {...}, ui_panels: {...}, defaults: {...} }`. v1→v2 migration in `_migrate()`. Read-only vault → `_persist()` dispatches an `sg-toast` warning instead of writing.

Default plugin enablement (still keyed by the legacy type_id strings): `linux=true`, `docker=true`, `elastic=true`, `vnc=true`, `prometheus=false`, `opensearch=false`, `neko=false`.

---

### CI hooks for the UI

- `tests/ci/test_wheel_contains_ui.py` — pins that the published wheel includes `sgraph_ai_service_playwright__api_site/` assets.
- `tests/ci/test_sg_compute_spec_detail__snapshot.py` (13 assertions) + `tests/ci/test_sg_compute_ami_picker__snapshot.py` (17 assertions) — pin the structural shape of two key components after the T3.3b rename.

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Sources (historical): [`_archive/v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md`](../_archive/v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md), [`14__sp-cli-ui-sg-layout-vnc-wiring.md`](../_archive/v0.1.31/14__sp-cli-ui-sg-layout-vnc-wiring.md), [`15__sp-cli-ui-dev-agent-dashboard.md`](../_archive/v0.1.31/15__sp-cli-ui-dev-agent-dashboard.md)
- Backend routes consumed: [`cli/observability.md`](../cli/observability.md), [`sg-compute/index.md`](../sg-compute/index.md) (`/api/specs/*`, `/api/amis`, etc.)
- Settings persistence in vault: [`vault/index.md`](../vault/index.md)
- Current dashboard component table mirror: [`sg-compute/index.md`](../sg-compute/index.md)
