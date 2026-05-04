# SG/Compute Frontend — Handover Brief

**Date:** 2026-05-04
**From:** Backend Sonnet session (claude/continue-playwright-refactor-xbI4j)
**To:** Frontend Sonnet session
**Status of backend:** ALL backend phases (B1–B8) complete
**Status of frontend:** ZERO F-phases started — starting from scratch

---

## 1. What you are working on

This is the **frontend track** of the SG/Compute migration brief. The backend has finished renaming `ephemeral_ec2/` → `sg_compute/`, building a typed spec catalogue, and wiring a real compute control-plane API (`Fast_API__Compute`). The dashboard currently has none of this wired in.

Your job: **update the dashboard** (`sgraph_ai_service_playwright__api_site/`) so it speaks the new vocabulary, consumes the new API, and gets its spec list from the server instead of a hardcoded constant.

---

## 2. Reference documents (read before touching code)

Read these in order:

| File | What it is |
|------|------------|
| `team/comms/briefs/v0.1.140__sg-compute__migration/00__README.md` | Strategy, product name, taxonomy |
| `team/comms/briefs/v0.1.140__sg-compute__migration/01__architecture.md` | API contracts, schema field names, platform/spec/node vocabulary |
| `team/comms/briefs/v0.1.140__sg-compute__migration/20__frontend-plan.md` | **Your full phase-by-phase task list** — F1 through F10 |
| `team/comms/briefs/v0.1.140__sg-compute__migration/30__migration-phases.md` | Which phases block which; exit criteria per phase |

---

## 3. Taxonomy cheat-sheet (memorise before touching any label)

| Old word | New word | Meaning |
|----------|----------|---------|
| Plugin | **Spec** | A recipe/type that defines what runs on a node (`docker`, `firefox`, …) |
| Stack (single instance) | **Node** | One running EC2 instance |
| Stack (multi-node) | **Stack** | Multiple nodes launched together (future concept) |
| Container | **Pod** | A Docker container running inside a node |
| type_id | **spec_id** | The string identifier for a spec |
| stack_name / stack_id | **node_id** / **node_name** | The identifier for a running node |
| container_count | **pod_count** | Count of containers in a node |

---

## 4. What the backend now serves

### `Fast_API__Compute` — live API surface

All endpoints are live and tested. Base path: `/api/`

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/api/health` | `{status: "ok"}` |
| `GET` | `/api/health/ready` | `{status, specs_loaded}` |
| `GET` | `/api/specs` | `Schema__Spec__Catalogue` — list of all specs |
| `GET` | `/api/specs/{spec_id}` | `Schema__Spec__Manifest__Entry` — one spec |
| `GET` | `/api/nodes` | `{nodes: [...], total: N}` — all EC2 nodes |
| `GET` | `/api/nodes/{node_id}` | `Schema__Node__Info` |
| `DELETE` | `/api/nodes/{node_id}` | `{node_id, deleted: bool}` |
| `GET` | `/api/pods` | `{pods: [], total: 0}` (placeholder) |
| `GET` | `/api/stacks` | `{stacks: [], total: 0}` (placeholder) |
| Per-spec | `/api/specs/docker/stacks` etc. | Spec-specific create/list/delete |

### `Schema__Node__Info` field names (what `GET /api/nodes` returns per node)

```js
{
  node_id:       "fast-fermi",        // was: stack_name
  spec_id:       "docker",            // was: type_id
  region:        "eu-west-2",
  state:         "ready",             // BOOTING | READY | TERMINATING | TERMINATED | FAILED
  public_ip:     "1.2.3.4",
  private_ip:    "10.0.0.1",
  instance_id:   "i-0abc123",
  instance_type: "t3.medium",
  ami_id:        "ami-xxx",
  uptime_seconds: 3600
}
```

### `Schema__Spec__Manifest__Entry` field names (what `GET /api/specs` returns per spec)

```js
{
  spec_id:              "docker",
  display_name:         "Docker host",
  icon:                 "🐳",
  version:              "0.1.0",
  stability:            "stable",           // stable | experimental | deprecated
  nav_group:            "CONTAINERS",       // BROWSERS | DATA | OBSERVABILITY | AI | DEV | OTHER
  capabilities:         ["vault-writes"],
  boot_seconds_typical: 600,
  create_endpoint_path: "/api/specs/docker/stack",
  extends:              [],
  soon:                 false
}
```

The catalogue currently returns **12 specs**: docker, podman, vnc, elastic, opensearch, firefox, neko, prometheus, ollama, open_design, playwright, mitmproxy.

---

## 5. Current dashboard state (what you inherit)

### Static hardcoded CATALOG in `sp-cli-compute-view.js`

`sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-compute-view/v0/v0.1/v0.1.0/sp-cli-compute-view.js`, lines 4–14:

```js
// ── Spec catalogue (static until backend phase B4 ships /api/specs) ─────────
const CATALOG = [
    { group: 'CONTAINERS',      type_id: 'docker',     ... create_endpoint_path: '/docker/stack'     },
    { group: 'CONTAINERS',      type_id: 'podman',     ... create_endpoint_path: '/podman/stack'     },
    { group: 'OBSERVABILITY',   type_id: 'elastic',    ... create_endpoint_path: '/elastic/stack'    },
    ...8 entries total, missing: ollama, open_design, playwright, mitmproxy
]
```

**B4 has shipped. This static array must go.**

### Hardcoded PLUGIN_ORDER in `sp-cli-launcher-pane.js`

`sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-launcher-pane/v0/v0.1/v0.1.0/sp-cli-launcher-pane.js`, line 4:

```js
const PLUGIN_ORDER = ['docker', 'podman', 'elastic', 'vnc', 'prometheus', 'opensearch', 'neko', 'firefox']
```

Missing 4 specs. Drives which `<sp-cli-{name}-card>` elements are created. **Must be replaced by catalogue data.**

### Hardcoded plugin toggles in `settings-bus.js`

`shared/settings-bus.js`, lines 10–21 — the `DEFAULTS.plugins` object hardcodes 8 spec names. Adding a spec requires editing this file. **Must become catalogue-driven.**

### API client calls legacy URLs

`admin/admin.js`, lines 259–260:
```js
apiClient.get('/catalog/types'),   // → must become GET /api/specs
apiClient.get(`/catalog/stacks${regionParam}`),   // → must become GET /api/nodes
```

### Event vocabulary (old naming, still wired)

`admin/admin.js` line 67: `sp-cli:stack.selected`, `sp-cli:stack.deleted`, `sp-cli:stacks.refresh`
`admin/admin.js` line 75: `sp-cli:plugin.toggled`
`admin/admin.js` line 118: `sp-cli:plugin:{name}.launch-requested`

These work but use the old vocabulary. Wire event rename lands in F4.

### Settings view HTML is mostly already updated

`sp-cli-settings-view.html` already says "Compute Specs" and "spec" in the section heading. But still has `class="plugin-list"` in the DOM and the JS underneath still uses `plugin*` names. Verify before claiming F1 done.

---

## 6. Recommended starting sequence

The frontend plan defines F1–F10. Do them in this order within the first session:

### Phase F1 — Terminology (pure copy-edit, lowest risk)

**Goal:** Every user-visible string uses Node/Spec/Pod vocabulary.

Key files to grep and fix:
- `sp-cli-compute-view.html` — "Stack" → "Node" everywhere
- `sp-cli-launcher-pane.html` — any "plugin" / "stack" copy
- `sp-cli-settings-view.html` + `.js` — `plugin-list` CSS class (class name OK for now, copy text matters)
- `admin.js` — `_activity()` strings mentioning "stack" or "plugin"
- Any toast strings

Do NOT change: web component tag names, event names, API URLs, file names.

### Phase F2 — API client (wire to real backend)

**Goal:** `GET /api/specs` and `GET /api/nodes` replace the two legacy calls.

Steps:
1. Add `useLegacyApiBase` toggle to `settings-bus.js` (default `false`).
2. Update `admin/admin.js` lines 259–260:
   - `/catalog/types` → `/api/specs`
   - `/catalog/stacks` → `/api/nodes`
3. Update field name consumers: `type_id` → `spec_id`, `stack_name` → `node_id` everywhere in the active-nodes rendering path.
4. Update per-spec create calls: e.g. `POST /docker/stack` → `POST /api/specs/docker/stack`.

### Phase F5 — Replace PLUGIN_ORDER and CATALOG with catalogue-driven discovery

**Goal:** No more hardcoded spec lists anywhere. The server is the source of truth.

Steps:
1. Create `shared/spec-catalogue.js`:
   ```js
   // Fetches GET /api/specs and caches for page lifetime.
   // Emits sp-cli:catalogue.loaded on document.
   // Exports getCatalogue() → { specs: [...] }
   ```
2. Update `sp-cli-compute-view.js`: delete the `CATALOG` constant; use `getCatalogue().specs` instead.
3. Update `sp-cli-launcher-pane.js`: delete `PLUGIN_ORDER`; iterate `getCatalogue().specs` filtered by `settings-bus` toggles.
4. Update `settings-bus.js` `DEFAULTS.plugins`: remove the hardcoded 8-entry object; on first load, populate from the catalogue so new specs are enabled by default.
5. Remove dead `import { loadCatalog } from './catalog.js'` once `shared/catalog.js` is superseded.

**Acceptance:** adding a 13th spec to the backend makes it appear in the launcher on next reload — no frontend change required.

---

## 7. Key file paths

```
sgraph_ai_service_playwright__api_site/
  admin/
    admin.js                          ← main controller (event wiring, API calls)
    index.html                        ← <script> tags loading all components
  shared/
    api-client.js                     ← HTTP client (GET/POST/DELETE)
    catalog.js                        ← OLD: /catalog/types cache — replace with spec-catalogue.js
    settings-bus.js                   ← plugin toggles, defaults, persistence
  components/sp-cli/
    sp-cli-compute-view/              ← main launch UI, contains static CATALOG
    sp-cli-launcher-pane/             ← top-bar cards, contains PLUGIN_ORDER
    sp-cli-settings-view/             ← settings panel (mostly already updated)
    sp-cli-events-log/                ← event filter pills
    sp-cli-stacks-pane/               ← active nodes list (uses "stack" naming)
    sp-cli-{name}-detail/             ← one per spec (docker, elastic, vnc, …)
```

---

## 8. Constraints (non-negotiable)

- **No build toolchain.** Native ES modules. Plain CSS. Web Components with Shadow DOM.
- **Three-file pattern** per component: `.js` + `.html` + `.css` under `{name}/v0/v0.1/v0.1.0/`.
- **Component tag names stay `sp-cli-*` until F9** — do not rename them in F1/F2/F5.
- **No Pydantic / no framework** — this is frontend only; no backend Python changes expected.
- **Branch:** `claude/sg-compute-frontend-{phase}-{description}-{session-id}`.
- **One PR per phase**, tagged `phase-F{N}__short-name`.
- **Reality doc update** not required yet (the UI domain hasn't been migrated to the domain tree) — note any changes in the PR description instead.

---

## 9. What you do NOT need to do (deferred)

- **F3** (Specs browse view) — new component, defer to next session.
- **F4** (wire-event rename `stack.*` → `node.*`) — defer; current aliases work.
- **F6** (per-spec UI co-location into `sg_compute_specs/<name>/ui/`) — defer; needs backend static-serving endpoint decision first.
- **F7** (Stacks placeholder view) — trivial but not urgent.
- **F8** (host-plane `/containers/` → `/pods/` URL update) — defer to after host plane is fully wired.
- **F9/F10** (cosmetic rename, dashboard move) — well-deferred.

---

## 10. Quick sanity test before you ship F2+F5

After wiring, manually verify:
1. Dashboard boots at `http://localhost:{port}/admin/`.
2. Compute view shows spec cards for all 12 specs (not just 8).
3. Clicking a card pre-fills the launch form.
4. `GET /api/nodes` call appears in browser DevTools Network tab (not `/catalog/stacks`).
5. `GET /api/specs` call appears (not `/catalog/types`).
6. Enabling/disabling a spec in settings shows/hides its card immediately.
7. Adding a 13th spec to the backend (edit a manifest) and reloading the page makes it appear — no frontend change needed.
