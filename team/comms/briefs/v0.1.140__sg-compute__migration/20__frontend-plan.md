# 20 — Frontend Sonnet Team: Implementation Plan

**Audience:** the frontend Sonnet team
**Prerequisites:** read [`00__README.md`](00__README.md) and [`01__architecture.md`](01__architecture.md) in full. Read [`30__migration-phases.md`](30__migration-phases.md) for cadence and what blocks what.

The frontend tracks the backend by one phase. The backend phases that bind you are: phase 4 (control plane FastAPI lands) and phase 6 (host plane pod rename). Most of your work is **terminology** + **API client** + **new views** — not visual design. **Defer the cosmetic component-prefix rename (`sp-cli-*` → `sg-compute-*`) to phase 9.**

Branch naming: `claude/sg-compute-frontend-{phase}-{description}-{session-id}`.

---

## Phase F1 — Terminology in user-facing labels (zero structural change)

**Goal:** Every label, badge, button, and pane title uses the new vocabulary. Web component names, file paths, CSS classes, and event names **do not change** in this phase. This is a copy-edit pass that establishes the new vocabulary in the UI without touching shape.

**Tasks:**

1. **Settings view** (`sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-settings-view/v0/v0.1/v0.1.0/sp-cli-settings-view.html`):
   - Section heading "Plugins" → "Specs".
   - Per-row label "Plugin: firefox" → "Spec: firefox".
   - Toggle help text updated.
2. **Compute view** / launcher pane (`sp-cli-compute-view`, `sp-cli-launcher-pane`):
   - Section heading "Active stacks" → "Active nodes".
   - Empty state copy "No stacks running" → "No nodes running".
   - Card subtitle "Stack type" → "Spec".
3. **Stack-detail-related labels** (`sp-cli-stacks-pane`, per-spec detail headers):
   - "Stack name" → "Node name".
   - "Stack ID" → "Node ID".
   - "Stack status" → "Node status".
   - Status pill copy: "Stack running" → "Node running"; "Stack stopped" → "Node stopped".
4. **Launch panel** (`sp-cli-launch-panel`, `sp-cli-launch-form`):
   - Form title "Launch stack" → "Launch node".
   - Field label "Stack name" → "Node name (auto if blank)".
   - Submit button "Launch stack" → "Launch node".
5. **Events log** (`sp-cli-events-log`):
   - Filter group label "Stack events" → "Node events".
   - Event display strings — leave the dotted event names alone (`sp-cli:stack.launched` etc. — these are wire events; rename in F4); but the human-readable label "Stack launched" → "Node launched".
6. **Top bar / header** — if any text says "SP" or "SGraph Playwright" or "Stack admin", change to "SG/Compute" / "Compute admin".
7. **Toasts** — any toast string with "stack" or "plugin" — replace.
8. **`sp-cli-launcher-pane`** card subtitle/text:
   - "Plugin: firefox" → "Spec: firefox" (or remove the noun entirely, the icon + display name is enough).

**What you do NOT touch in F1:**

- Web component tag names (`<sp-cli-launcher-pane>`).
- File names, folder names.
- `customElements.define()` calls.
- CSS selectors, class names.
- Event names dispatched on document.
- API client URLs (those land in F2).

**Acceptance criteria:**

- A grep across `sgraph_ai_service_playwright__api_site/` for user-facing strings shows: zero "Plugin" / "Plugins" labels; zero "Stack" labels for single-instance entities; "Node" used consistently for instances; "Spec" used consistently for types.
- Existing functionality unchanged. The dashboard still talks to today's `Fast_API__SP__CLI` URLs.
- Snapshot tests for any settings/launcher views are updated.

**Ship as one PR. Tag `phase-F1__terminology-labels`.**

---

## Phase F2 — API client migration

**Goal:** The dashboard's `api-client.js` is updated to call the new `/api/{nodes,pods,specs,stacks}` URLs. The legacy `Fast_API__SP__CLI` URLs are kept available behind a feature flag (default off) so the dashboard can roll back in one toggle.

**Blocked by:** backend phase 4 (the new `Fast_API__Compute` is live and serving the `/api/...` surface).

**Tasks:**

1. Add a feature toggle in `settings-bus.js` named `useLegacyApiBase` (default `false`).
2. Update `shared/api-client.js`:
   - Base path resolves to `/api/` when `useLegacyApiBase === false` (the default), or to the legacy paths when `true`.
   - URL maps:
     - `POST /xxx/stack` → `POST /api/specs/{spec_id}` (or `POST /api/nodes` with body `{ spec: <id> }` per architecture §1) — pick one based on the route catalogue the backend ships in phase 4.
     - `GET  /catalog/types` → `GET /api/specs`.
     - `GET  /catalog/stacks` → `GET /api/nodes`.
     - `GET  /xxx/stack/{id}` → `GET /api/nodes/{id}`.
     - `DELETE /xxx/stack/{id}` → `DELETE /api/nodes/{id}`.
     - Per-host endpoints (`/containers/list`, `/host/status`, etc.) — these come from the host plane proxied through the control plane. Update once backend phase 6 lands; until then keep legacy.
3. Mirror the new schemas from backend (`Schema__Node__Info`, `Schema__Pod__Info`, `Schema__Spec__Manifest__Entry`) — frontend doesn't validate, but it should consume the field names correctly:
   - `stack_id` → `node_id` everywhere.
   - `type_id` (in card STATIC blobs) → `spec_id`.
   - `container_count` (host-status) → `pod_count`.
4. Update every consumer (settings-bus default-types, launcher pane, stacks pane, per-spec detail components) to read the new field names. Use grep to find every occurrence.
5. Add an integration test: spin up the new control plane in-process; the dashboard renders against it.

**Acceptance criteria:**

- The dashboard works end-to-end against `Fast_API__Compute`.
- `useLegacyApiBase: true` switches it back to the legacy app — manual smoke test confirms.
- All field-name renames are covered (no `stack_id` references remain in the new code path).
- Snapshot tests updated.

**Ship as one PR. Tag `phase-F2__api-client`.**

---

## Phase F3 — Add the Specs view (left nav + browse pane)

**Goal:** The left nav gains a Specs item. Clicking it opens a "browse the catalogue" view that lists every available spec with its manifest details. This is a new view, not a rename of an existing one.

**Tasks:**

1. Add `<sp-cli-specs-view>` web component under `components/sp-cli/sp-cli-specs-view/v0/v0.1/v0.1.0/`.
2. Renders a grid (or list) of specs from `GET /api/specs`. Per spec card shows:
   - Icon (manifest `icon`).
   - Display name + spec_id.
   - Stability badge.
   - Capability chips (vault-writes, mitm-proxy, etc.).
   - Version (from `manifest.version`).
   - Boot time estimate.
   - "Launch a node" button — opens the launch flow with `--spec <id>` pre-filled.
3. Per-spec detail (clicking a card) opens a tab `<sp-cli-spec-detail>` showing:
   - Full manifest as a structured panel.
   - The `extends` lineage (visualised as a small DAG).
   - List of AMIs baked from this spec (placeholder until backend ships AMI list endpoint — currently in §8 of the post-fractal-UI brief).
   - Link to the spec's README (mounted at `/api/specs/{id}/readme` per backend phase 4).
4. Add to left nav (`sp-cli-left-nav`): new item `data-view="specs"` between "Compute" and "Settings".
5. Wire `sp-cli:nav.selected` listener to mount `<sp-cli-specs-view>` in the main column.

**Acceptance criteria:**

- "Specs" appears in the left nav.
- Clicking it shows a grid of all installed specs.
- Each spec card is keyboard-navigable, has WCAG AA contrast.
- Empty state ("No specs installed — install a `*-compute-specs` package") renders correctly.

**Ship as one PR. Tag `phase-F3__specs-view`.**

---

## Phase F4 — Wire-event vocabulary update (`sp-cli:stack.*` → `sp-cli:node.*`)

**Goal:** The dashboard's internal event vocabulary aligns with the new taxonomy. Web component names still stay as `sp-cli-*`; only event names migrate. This is the prerequisite for phase 9.

**Tasks:**

1. Update emitters: `sp-cli:stack.launched` → `sp-cli:node.launched`, `sp-cli:stack.selected` → `sp-cli:node.selected`, `sp-cli:stacks.refresh` → `sp-cli:nodes.refresh`, `sp-cli:stack.deleted` → `sp-cli:node.deleted`.
2. Update listeners in `admin/admin.js`.
3. Per-spec event names: `sp-cli:plugin:firefox.launch-requested` → `sp-cli:spec:firefox.launch-requested`. Update emitters (per-spec cards) and listeners (admin.js).
4. Keep back-compat aliases: dispatch BOTH `sp-cli:stack.launched` AND `sp-cli:node.launched` for one release. Listen for both. Mark the legacy names DEPRECATED in `sp-cli-events-log.js:14` `FAMILIES` map.
5. Update the events-log filter pills (`sp-cli-events-log`) to use the new family names.
6. Update the post-fractal-UI brief 05 (governance — event vocabulary spec) to reflect the rename. The deprecated list now includes the old event names plus their migration deadline.

**Acceptance criteria:**

- Both event-name forms work in this release.
- Snapshot tests cover the new emitters.
- The `FAMILIES` map in `sp-cli-events-log.js` lists every event with its status (ACTIVE / RESERVED / DEPRECATED).

**Ship as one PR. Tag `phase-F4__event-vocabulary`.**

---

## Phase F5 — Settings: replace `PLUGIN_ORDER` with manifest-driven discovery

**Goal:** The dashboard fetches `GET /api/specs` once at boot, caches the response, and renders cards / settings from that — not from the four hard-coded sites.

This is **the same item as `01__plugin-manifest-loader.md` from the post-fractal-UI brief**, restated under the new taxonomy. It blocks phase F6 (per-spec UI co-location).

**Tasks:**

1. Create `shared/spec-catalogue.js` — replaces the four hardcoded `PLUGIN_ORDER` / `LAUNCH_TYPES` / `settings-bus.DEFAULTS` / `index.html` script tags.
2. On dashboard boot, call `GET /api/specs` and populate the catalogue.
3. Emit `sp-cli:catalogue.loaded` once.
4. Refactor:
   - `sp-cli-launcher-pane.js` — iterates `getCatalogue().specs` instead of `PLUGIN_ORDER`.
   - `admin.js` — listener wiring loops over the catalogue.
   - `settings-bus.js` — defaults computed from the catalogue.
5. Keep the legacy `<script>` tags in `admin/index.html` (they load the per-spec UI components) — until phase F6 moves the components into the spec folders.

**Acceptance criteria:**

- Adding a new spec on the backend (without a frontend code change) makes its card appear in the dashboard on next reload.
- Removing a spec on the backend makes the card disappear; existing settings are not lost (just hidden).
- All four legacy duplication sites are removed (or reduced to a single comment pointing at `spec-catalogue.js`).

**Ship as one PR. Tag `phase-F5__catalogue-loader`.**

---

## Phase F6 — Move per-spec UI into `sg_compute_specs/<name>/ui/`

**Goal:** Each spec's card + detail components live under the spec's own folder, not under the dashboard tree. The dashboard fetches them dynamically from `/api/specs/{id}/ui/...`.

**Blocked by:** backend phases 3.x (specs migrated to `sg_compute_specs/`) and the per-spec UI-serving endpoint (backend plan addendum needed — flag in §Open questions).

**Tasks (per-spec, repeat for each migrated spec):**

1. Move `sgraph_ai_service_playwright__api_site/plugins/<name>/v0/v0.1/v0.1.0/` → `sg_compute_specs/<name>/ui/card/`.
2. Move `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-<name>-detail/v0/v0.1/v0.1.0/` → `sg_compute_specs/<name>/ui/detail/`.
3. Update `admin/index.html` script tags: per-spec components are now loaded from `/api/specs/{id}/ui/card/sp-cli-{name}-card.js` (etc.) instead of relative paths.
4. Verify the dashboard still renders the spec's card + detail.

**Acceptance criteria:**

- Each migrated spec's UI lives **inside** the spec's folder; dashboard tree no longer carries per-spec UI files for migrated specs.
- A spec installed from a third-party package (`acme-compute-specs`) renders its UI in the dashboard transparently.
- No regression in card / detail rendering.

**Ship one PR per spec, tagged `phase-F6__<spec>-ui-colocation`.**

---

## Phase F7 — Stacks (multi-node) view (placeholder)

**Goal:** A new left-nav item "Stacks" exists with a placeholder view explaining what stacks will be ("multi-node combinations launched together"). No functional stack creation yet — backend stacks are placeholder routes in phase 4.

**Tasks:**

1. Add `<sp-cli-stacks-overview-view>` (different name from `sp-cli-stacks-pane` which is the active-nodes list).
2. Renders a "Stacks coming soon" placeholder + 2-3 example stack definitions read from a static JSON in the dashboard for now.
3. Wire to left nav.

**Acceptance criteria:** the nav item exists; the placeholder view renders. No functional stack creation expected until a future phase.

**Ship as one PR. Tag `phase-F7__stacks-placeholder`.**

---

## Phase F8 — Host-plane URL update (containers → pods)

**Blocked by:** backend phase 6.

**Tasks:**

1. Update `api-client.js`: every reference to `/containers/...` → `/pods/...`.
2. Update any UI label that says "Container" referring to a Docker container inside a node — replace with "Pod".
3. Update field names: `container_count` → `pod_count` in `Schema__Host__Status` consumer code.

**Acceptance criteria:** the dashboard reflects "pods" everywhere host-related.

**Ship as one PR. Tag `phase-F8__host-pods`.**

---

## Phase F9 — Cosmetic component-prefix rename `sp-cli-*` → `sg-compute-*`

**Goal:** Web component names align with the new brand. This is a sweep across every component file, every `customElements.define()`, every HTML reference, every CSS host selector.

**Strategy:** automate as much as possible with `git mv` + repository-wide string replace, then test thoroughly.

**Tasks:**

1. For every component directory under `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-{name}/`:
   - `git mv sp-cli-{name} sg-compute-{name}`.
   - Inside the component's `.js` file: `class SpCli{Name} extends ...` → `class SgCompute{Name} extends ...`; `customElements.define('sp-cli-{name}', ...)` → `customElements.define('sg-compute-{name}', ...)`.
   - Inside the component's `.html` file: any reference to a sibling component tag.
   - Inside the component's `.css` file: `:host(sp-cli-{name})` selectors.
2. Update every `<script type="module">` in `admin/index.html` and `user/index.html`.
3. Update every `document.createElement('sp-cli-{name}-...')` and `document.querySelector('sp-cli-...')`.
4. Repeat for the `_shared/sg-remote-browser` family — those already use `sg-` prefix and stay.
5. Update test snapshots; rename test file paths.
6. Update reality doc (UI domain).

**Acceptance criteria:**

- A grep across `sgraph_ai_service_playwright__api_site/` (or the migrated `sg_compute/frontend/` if F-frontend-move has happened) for `sp-cli-` returns zero results.
- All snapshot tests pass.
- Manual smoke test: dashboard boots, every view renders, every interaction works.

**Ship as one PR. Tag `phase-F9__component-prefix-rename`.**

---

## Phase F10 (deferred) — Move dashboard into `sg_compute/frontend/`

**Goal:** `sgraph_ai_service_playwright__api_site/` → `sg_compute/frontend/`. After F9 has run, every component name is already aligned; this is just the directory move.

This phase **may slip into a separate brief** depending on how much risk we want in one window. Flag.

---

## Cross-cutting frontend rules

- **No build toolchain.** Native ES modules. Plain CSS. Web Components with Shadow DOM. No Tailwind / SCSS / utilities.
- **Three-file pattern**: `.js` + `.html` + `.css` siblings under `{name}/v0/v0.1/v0.1.0/`.
- **Custom-element naming**: until F9, keep `sp-cli-*`. After F9, `sg-compute-*`. NEW components added during F1-F8 may use either prefix; recommend `sg-compute-*` for new components to reduce F9's scope.
- **Events on `document`** with `{ bubbles: true, composed: true }`. No reaching into shadow DOM from the controller.
- **Accessibility**: WCAG AA contrast, keyboard navigation, ARIA labels on icon-only controls.
- **Density**: this is an operator tool. More info per screen, not less.
- **Branch:** `claude/sg-compute-frontend-{phase}-{description}-{session-id}`.
- **PR title**: `phase-F{N}: {short summary}`.

---

## Open questions to flag with the UI Architect

- **Per-spec UI serving** (F6) — does the backend need a new `GET /api/specs/{id}/ui/{path}` endpoint, or do we serve UI as static assets via the FastAPI `StaticFiles` mount?
- **Spec card template** — today each spec card has its own `.html` file (firefox-card, docker-card, etc.). With manifest-driven discovery (F5), is there a single template that consumes the manifest? Recommend: yes, a single `<sg-compute-spec-card>` parameterised by the manifest entry. Card reuses the manifest; per-spec custom card visuals stay possible via a `<slot>`.
- **Light mode** — out of scope; raise as a follow-up brief.
