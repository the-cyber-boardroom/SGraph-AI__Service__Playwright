# Reality — SP CLI UI v2 (sg-layout) + VNC Wiring — Slice 14

**Added:** 2026-04-29  
**Branch:** `claude/setup-dev-agent-ui-titBw`  
**Picks up from:** Slice 13 (MVP admin/user UI with polling; old Web Components replaced)

---

## What exists after this slice

### UI architecture change — sg-layout fractal panes

The polling-based flat-layout UI from slice 13 was replaced. The new UI uses
`<sg-layout>` (CDN `https://dev.tools.sgraph.ai/core/sg-layout/v0.1.0/`), a fractal
splitter/tab container. Each pane is a custom element using the `SgComponent` 3-file
pattern (`.js` + `.html` + `.css`), shadow DOM, `static jsUrl = import.meta.url`.

Vault authentication is handled by:
- `<sg-vault-connect>` (CDN) — credentials form inside the vault-picker dropdown
- `vault-bus.js` — page-level vault state; `startVaultBus()`, `getRestorablePrefill()`
- Auto-connect via `_tryAutoConnect()` — clicks the Connect button in sg-vault-connect's
  shadow DOM when saved credentials exist (`sg-vault:last-key`, `sg-vault:last-api`)

---

### Shared utilities (`api_site/shared/`)

| File | Purpose |
|------|---------|
| `api-client.js` | Module singleton `ApiClient`; reads `sg_api_url`/`sg_api_key` from localStorage; defaults URL to `window.location.origin`; 401 → `sg-auth-required` event |
| `vault-bus.js` | Vault state management; `startVaultBus()`, `vaultReadJson()`, `vaultWriteJson()`, `isConnected()`, `isWritable()` |
| `components/sg-auth-panel.js` | Auth panel Web Component; listens for `sg-auth-required`; opens drawer to set API URL + key |

---

### sp-cli Web Components (`api_site/components/sp-cli/`)

All follow `SgComponent` base class from CDN. All component CSS files include
`[hidden] { display: none !important }` to prevent `display: flex/grid` from
overriding the `hidden` attribute.

| Component | Version | Role |
|-----------|---------|------|
| `sp-cli-top-bar` | v0.1.0 | Top bar: page title slot + region-picker slot + vault-picker slot |
| `sp-cli-region-picker` | v0.1.0 | Region selector dropdown; emits `sp-cli:region-changed { region }` |
| `sp-cli-vault-picker` | v0.1.0 | Vault connection dropdown; embeds `<sg-vault-connect>`; "Token settings" button shows reconnect form; auto-connects on page load when credentials are saved |
| `sp-cli-catalog-pane` | v0.1.0 | sg-layout pane; `setTypes(entries)` renders type cards with Launch buttons; emits `sp-cli:catalog-launch { entry }` |
| `sp-cli-stacks-pane` | v0.1.0 | sg-layout pane; `setStacks(stacks)` renders active stack rows; emits `sp-cli:stacks-refresh`, `sp-cli:stack-selected { stack }` |
| `sp-cli-activity-pane` | v0.1.0 | sg-layout pane; listens for `sp-cli:activity-entry { message }`; reverse-chronological log; Clear button |
| `sp-cli-vault-activity` | v0.1.0 | sg-layout pane; listens for `sp-cli:vault-bus:*` events; shows vault read/write trace |
| `sp-cli-user-pane` | v0.1.0 | Combined pane for user page: available-type cards (top) + active-stacks strip (bottom); emits `sp-cli:user-launch { entry }`, `sp-cli:stack-selected { stack }` |
| `sp-cli-launch-modal` | v0.1.0 | Launch wizard modal; `open(entry)` shows stack-name + instance-type + max-hours form; POSTs to `entry.create_endpoint_path`; emits `sp-cli:launch-success { entry, response }`, `sp-cli:launch-error { entry, error }` |
| `sp-cli-stack-detail` | v0.1.0 | sg-layout pane (right column); listens to `sp-cli:stack-selected` directly; shows empty state by default; fetches `GET /{type}/stack/{name}` for full detail; Delete with inline confirm → `DELETE /{type}/stack/{name}`; emits `sp-cli:stack-deleted { stack }` |

**Timing guards:** all `set*()` methods buffer their data if the component's `onReady()`
has not yet fired (sg-layout creates elements dynamically after data may have arrived).

---

### Admin dashboard (`api_site/admin/`)

**Layout** (3 columns, saved to `localStorage` key `sp-cli:admin:layout:v2`):
```
row [
  sp-cli-catalog-pane          (~42%)
  column [
    sp-cli-stacks-pane         (~55% of middle column)
    sp-cli-activity-pane       (~45% of middle column)
  ]                            (~36%)
  column [
    sp-cli-vault-activity
    sp-cli-stack-detail        ← tabs
  ]                            (~22%)
]
```

**Page controller (`admin.js`) event wiring:**

| Event | Handler |
|-------|---------|
| `vault:connected` | `_setGate(true)` → `_initLayout()` → `_loadData()` |
| `vault:disconnected` | `_setGate(false)` |
| `sp-cli:stacks-refresh` | `_loadData()` |
| `sg-auth-saved` | `_loadData()` |
| `sp-cli:region-changed` | store `_region`, `_loadData()` |
| `sp-cli:catalog-launch` | `_openModal(entry)` |
| `sp-cli:user-launch` | `_openModal(entry)` |
| `sp-cli:launch-success` | activity log entry + `_loadData()` after 3 s |
| `sp-cli:launch-error` | activity log entry |
| `sp-cli:stack-deleted` | activity log entry + `_loadData()` |

`_loadData()` calls `GET /catalog/types` + `GET /catalog/stacks[?region=…]` in parallel
and pushes results to `sp-cli-catalog-pane.setTypes()` and `sp-cli-stacks-pane.setStacks()`.

**Vault gate:** `#vault-gate` is shown until `vault:connected`; `#main-content` is hidden.
`admin.css` contains `[hidden] { display: none !important }` to ensure `display: flex`
on the containers doesn't override the `hidden` attribute.

---

### User provisioning page (`api_site/user/`)

**Layout** (2 columns, saved to `localStorage` key `sp-cli:user:layout`):
```
row [
  sp-cli-user-pane    (100% — types + active stacks combined)
  sp-cli-vault-activity                                       (0% initially, user can resize)
]
```

**Page controller (`user.js`) event wiring:**

| Event | Handler |
|-------|---------|
| `vault:connected` | `_setGate(true)` → `_initLayout()` → `_loadData()` |
| `vault:disconnected` | `_setGate(false)` |
| `sg-auth-saved` | `_loadData()` |
| `sp-cli:region-changed` | store `_region`, `_loadData()` |
| `sp-cli:user-launch` | `_openModal(entry)` |
| `sp-cli:launch-success` | `_loadData()` after 3 s |
| `sp-cli:stack-deleted` | `_loadData()` |

---

### VNC wiring (completes `vnc-handover` tasks 04 + 05)

| File | Change |
|------|--------|
| `Fast_API__SP__CLI` | Added `vnc_service: Vnc__Service`; calls `vnc_service.setup()` in `setup()`; shares instance into `catalog_service.vnc_service`; mounts `Routes__Vnc__Stack` + `Routes__Vnc__Flows` |
| `Stack__Catalog__Service` | Added `vnc_service: Vnc__Service` field; added VNC branch in `list_all_stacks()` |

**VNC routes now live on `Fast_API__SP__CLI`:**

| Method | Path |
|--------|------|
| POST   | `/vnc/stack` |
| GET    | `/vnc/stacks` |
| GET    | `/vnc/stack/{name}` |
| DELETE | `/vnc/stack/{name}` |
| GET    | `/vnc/stack/{name}/health` |
| GET    | `/vnc/stack/{name}/flows` |

**Total routes on `Fast_API__SP__CLI`: 33**
(27 from slice 13 + 6 VNC).

---

### New primitive — `Safe_Str__Endpoint__Path`

**File:** `sgraph_ai_service_playwright__cli/catalog/primitives/Safe_Str__Endpoint__Path.py`

`Safe_Str__Text` was converting `/` to `_`, turning `/linux/stack` into
`_linux_stack` and producing broken fetch URLs in the UI. `Safe_Str__Endpoint__Path`
allows lowercase letters, digits, `/`, `-`, `_`, `{`, `}` — sufficient for all
API endpoint path patterns. Used for all five `*_endpoint_path` fields in
`Schema__Stack__Type__Catalog__Entry`.

---

### Schema changes

| Schema | Field | Change |
|--------|-------|--------|
| `Schema__Stack__Type__Catalog__Entry` | `create/list/info/delete/health_endpoint_path` | Type changed from `Safe_Str__Text` → `Safe_Str__Endpoint__Path` |
| `Schema__Stack__Type__Catalog__Entry` | `default_max_hours` | Default changed from `4` → `1` |

---

### Bug fixes

| Location | Fix |
|----------|-----|
| `Vnc__Service.list_stacks` | `region = region or DEFAULT_REGION` guard (was passing `''` to boto3, causing `https://ec2..amazonaws.com` invalid-endpoint 422) |
| All sp-cli component CSS | Added `[hidden] { display: none !important }` — `display: flex/grid` was overriding the `hidden` attribute, causing placeholder elements to remain visible after data loaded |

---

### Tests added

| Suite | New tests |
|-------|-----------|
| `test_Fast_API__SP__CLI.py` | `test_vnc_routes_are_mounted` + `test_vnc_service_is_wired` |

---

## Not included (PROPOSED — does not exist yet)

- `Routes__OpenSearch__Stack` not mounted on `Fast_API__SP__CLI`
- `Routes__Prometheus__Stack` not mounted on `Fast_API__SP__CLI`
- `Enum__Stack__Type.PROMETHEUS` does not exist
- Region filtering passed through to per-service `list_stacks` (catalog route accepts `?region=` but passes it only to VNC/Linux/Docker; Elastic uses its own `resolve_region`)
- Playwright/pytest UI smoke tests
- Auth beyond `X-API-Key`
