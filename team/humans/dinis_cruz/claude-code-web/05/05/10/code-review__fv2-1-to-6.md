# Code Review — FV2.1 through FV2.6

**Branch:** `dev` @ v0.2.1
**Review date:** 2026-05-05 10:xx UTC
**Reviewer:** Claude (deep-review mode, read-only)
**Scope:** Frontend slices FV2.1 → FV2.6 since v0.2.0.

Each phase below was checked by reading the brief in full, opening the implementing commit, diffing the changed files, then grepping the live tree for residual issues.

---

## FV2.1 — Centralise node-state vocabulary

**Commits:** `f63f204 phase-FV2.1: centralise node-state vocabulary`

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| `shared/node-state.js` exists with `NODE_STATE`, `isRunning`, `stateClass`, `stateLabel` | DONE | `sgraph_ai_service_playwright__api_site/shared/node-state.js:1-47` |
| `grep "=== 'running'" \| grep -v node-state.js` → 0 hits | DONE | grep returned 0 hits in active code |
| Helpers tolerant of legacy `'running'` | DONE | `node-state.js:13-16,21,28` keep the alias |
| 6 sites in `sp-cli-nodes-view.js` swept | DONE | `sg-compute-nodes-view.js:99,107,259,263,285,327` use `isRunning` |
| Detail components swept | DONE | elastic/firefox/vnc/prometheus/opensearch/cost-tracker/stacks-pane/user-pane all import `node-state.js` |

**Project-rule violations:**

- **Casing mismatch with brief.** Brief specified `BOOTING`, `READY`, `TERMINATING`, `TERMINATED`, `FAILED` (uppercase per the canonical `Enum__Node__State` shown in the brief). Implementation uses lowercase (`'booting'`, `'ready'` …). Backend `Enum__Node__State` actually uses lowercase string values (`sg_compute/primitives/enums/Enum__Node__State.py:9-13`), so the impl matches the wire format — but the `NODE_STATE` constant *names* keep the upper-case `BOOTING:` form, leaving an inconsistency where the constant lookup `NODE_STATE.READY` returns the literal `'ready'`. This is fine but worth a comment.

**Integration concerns:**

- `podPillClass(status)` hardcodes Docker container vocabulary (`'running'`, `'exited'`, `'dead'`) — that's appropriate (container lifecycle ≠ node lifecycle), but the asymmetry is undocumented and a future reviewer might mistakenly "fix" it through `isRunning`.

**Bad decisions / shortcuts:** none observed. The phase did exactly what the brief asked.

**Verdict:** Solid.

---

## FV2.2 — `/api/specs` + `/api/nodes` migration; field renames

**Commits:** `1eaacde FV2.2 — Switch dashboard to /api/specs + /api/nodes; field renames`

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| `useLegacyApiBase` toggle on `api-client.js` | MISPLACED | Lives on `settings-bus.js:10,53,57` (`use_legacy_api`); `api-client.js` itself has no toggle and no `/api/` prefixing helper. The brief's "Provide a single `apiClient.get('specs')` helper" was not built. |
| `admin.js` calls `/api/specs` + `/api/nodes` | DONE | `admin.js:273-280` (with `useLegacy` ternary fallback) |
| `POST /api/specs/{spec_id}/stack` for per-spec create | NOT DONE | The `sg-compute-launch-panel._launch()` still posts to `entry.create_endpoint_path` (= legacy `/<spec>/stack`) — `sg-compute-launch-panel.js:61`. Only `sg-compute-compute-view._launch()` (added in FV2.5) uses `/api/nodes`. |
| `stack_name` → `node_id` rename in active code | PARTIAL | admin.js uses `stack.node_id || stack.stack_name` fallback at 6 sites (118, 128, 139, 163, 219, 258, 294). Helpful for transition but the per-spec launch flow STILL submits `stack_name:` as the request body field (`sg-compute-launch-panel.js:46,49`, `sg-compute-launch-form.js:69`). |
| `type_id` → `spec_id` rename | PARTIAL | Same dual-read pattern: `entry.spec_id \|\| entry.type_id` at admin.js:129,151,166,220,240,259. Launch-form still calls `entry?.type_id` to seed name (`sg-compute-launch-form.js:64`). |
| `container_count` → `pod_count` | DONE in active path (no remaining reads found in dashboard JS). |
| Browser DevTools shows only `/api/*` | NEAR | Dashboard yes; **but** `user/user.js:76-77` still calls `/catalog/types` + `/catalog/stacks` unconditionally — FV2.2 only swept the admin tree. |
| Setting `useLegacyApiBase: true` flips back to legacy | MOSTLY | admin.js works; user.js was never wired. |

**Project-rule violations:**

- `api-client.js` retains `apiClient.post(absolute_path, body)`. The brief's `apiClient.get('specs')` (relative-name shortcut) was not built; every caller still hardcodes `/api/...`. Minor — the toggle moved to settings-bus and is read at the call-site instead.

**Integration concerns:**

- **`user/user.js` not migrated.** Lines 76-77 unconditionally hit `/catalog/types` / `/catalog/stacks`. The user dashboard is broken once `Fast_API__SP__CLI` moves under `/legacy/` (BV2.10) unless the legacy mount is still reachable.
- **Dual launch flows.** FV2.5 introduced a generic `/api/nodes` post in compute-view; the OLDER `sg-compute-launch-panel` still uses `entry.create_endpoint_path`. So `Specs view → Launch node` (FV2.4) opens the legacy panel; `Compute view → select card → Launch` (FV2.5) uses the new path. Two code paths, two payload shapes.
- The migration left `caller_ip: ''` hardcoded in launch-panel (`:53`) — backend FV2.5 work assumes server-side detection of the caller IP, but only the new compute-view path benefits.

**Bad decisions / shortcuts:**

- Six "fallback" reads of `stack.node_id || stack.stack_name` in admin.js encode the migration ambiguity into the code. They will silently hide a backend-side regression where one of the two field names disappears. Should be a single read once BV2.x stabilises.

**Verdict:** Has issues. Partial: the dashboard moved but the user app was not migrated; per-spec launch did not switch to `/api/specs/{id}/stack`; legacy field names persist on the request side.

---

## FV2.3 — `shared/spec-catalogue.js` + delete hardcoded plugin lists

**Commits:** `f7bee07 FV2.3 — spec-catalogue.js; delete hardcoded plugin lists`

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| `shared/spec-catalogue.js` exists with `loadCatalogue`, `getCatalogue`, `getSpec` | DONE | `shared/spec-catalogue.js:1-26` |
| Booted on dashboard load | DONE | `admin.js:47` |
| `sp-cli:catalogue.loaded` event dispatched | DONE | `spec-catalogue.js:12` |
| `PLUGIN_ORDER`, `CATALOG`, `LAUNCH_TYPES` removed | DONE | grep returns 0 hits |
| `DEFAULTS.plugins` → `{}` populated from catalogue | DONE | `settings-bus.js:11`, listener at `:133-145` |
| `shared/catalog.js` deleted | DONE | `find … catalog.js` returns no file |
| Adding 13th spec on backend → card appears with no FE change | PARTIAL | The catalogue lists it; but `admin/index.html` still has a hand-maintained `<script>` tag list (8 cards + 8 details). Adding `mitmproxy` / `ollama` / `open_design` / `playwright` to the catalogue without adding script tags = the card silently fails to define (admin.js comment at index.html:34-35 acknowledges this). The promise of "zero FE code change" only holds for the catalogue-listing layer; the rendering still requires HTML edits — that gap is what FV2.6 was supposed to close, and FV2.6 only moved the script tags, didn't auto-discover them. |

**Project-rule violations:** none.

**Integration concerns:**

- `getCatalogue()` throws if not loaded, and `loadCatalogue()` swallows errors at `admin.js:47` (`.catch(err => console.warn(...))`). On a 401 / network failure the dashboard runs without specs and most consumers (`compute-view._renderGroups`, `specs-view._render`) silently return. There is no user-visible error state.
- Cache is module-singleton with no invalidation API. Brief mentions "Spec catalogue → Reload" button (FV2.4) — not built. Any dynamic spec install requires a full page reload.

**Bad decisions / shortcuts:**

- The `<script>` tag list in `admin/index.html` is the de-facto authoritative card registry — it dictates which cards actually render. The catalogue is the source of truth for *data* but not for *rendering*. Effectively two registries.

**Verdict:** Solid for the data layer. The "zero FE code change" promise leaks because of `index.html`'s static `<script>` tags.

---

## FV2.4 — Specs view (left-nav item + browse pane)

**Commits:** `3315151 FV2.4 — sp-cli-specs-view; Specs left-nav item`

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| `<sp-cli-specs-view>` component (now `<sg-compute-specs-view>` post-FV2.12) | DONE | `components/sp-cli/sg-compute-specs-view/v0/v0.1/v0.1.0/` (3 files) |
| "Specs" left-nav item | DONE | added in `sg-compute-left-nav.html` per FV2.4 commit |
| Spec card renders icon + display_name + spec_id + stability badge + capability chips + version + boot estimate + Launch button | DONE | `sg-compute-specs-view.js:47-65` |
| Empty state | DONE | `sg-compute-specs-view.html:7-9` |
| Stability badge classes (stable / experimental / deprecated) | DONE | `_stabClass()` at `:80-84` |
| `<sp-cli-spec-detail>` ("View detail" link → spec detail tab) | MISSING | Brief Task 3 explicitly required a separate `<sp-cli-spec-detail>` component with manifest panel, `extends` lineage DAG, AMI list, README link. Not built. The card has no "View detail" link at all. |
| AMIs / README / extends lineage placeholders | MISSING | Same — no detail component, no placeholders. |
| Keyboard nav | PARTIAL | Cards are `<article>` listitems with a `<button>` Launch action. Not focusable as cards themselves; only the Launch button receives focus. Brief required the cards to be keyboard-navigable. |

**Project-rule violations:**

- "WCAG AA contrast on stability badges" — not verified here (would need contrast measurement). Grep shows colour classes exist but no automated check.
- Card is a non-interactive `<article role="listitem">`; the only keyboard target is the inner button. That meets "navigate to launch", not "browse the grid by keyboard".

**Integration concerns:**

- "Launch node" emits `sp-cli:catalog-launch` → admin.js opens `<sg-compute-launch-panel>` (the OLD launch flow). So FV2.4's launch button bypasses FV2.5's new `/api/nodes` path entirely and lands in the legacy `entry.create_endpoint_path` flow. **The "specs grid → launch" path will silently fail for any spec whose catalogue entry lacks `create_endpoint_path` — and the new generic launch is unreachable from the Specs view.**
- Listener wiring in admin.js for per-spec launch (`sp-cli:spec:{spec_id}.launch-requested`) is not what the specs-view emits — specs-view emits the legacy `sp-cli:catalog-launch` event.

**Bad decisions / shortcuts:**

- Brief's Task 3 (`<sp-cli-spec-detail>`) was silently dropped. No follow-up flag in the debrief.

**Verdict:** Has issues. Grid + nav item shipped; spec-detail tab missing; launch wiring goes through the legacy panel.

---

## FV2.5 — Launch flow with three creation modes (FRESH / BAKE_AMI / FROM_AMI)

**Commits:** `985ed96 FV2.5 — launch flow via POST /api/nodes (BV2.5 unblock)`

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| Form renders three-mode selector (FRESH / BAKE_AMI / FROM_AMI) | MISSING | No mode selector anywhere. `sg-compute-compute-view.html` and `sg-compute-launch-form.html` have only name/region/instance/hours fields. |
| Conditional reveal per mode | MISSING | n/a |
| AMI picker `<sp-cli-ami-picker>` | MISSING | No file under `_shared/`. |
| BAKE_AMI cost preview banner | MISSING | n/a |
| Submit blocked when FROM_AMI without AMI | MISSING | n/a |
| Form submits a body matching `Schema__Stack__Create__Request__Base` | NEAR | compute-view sends `{spec_id, node_name, region, instance_type, max_hours}` (`compute-view.js:183-189`). No `creation_mode` / `ami_id` / `bake_ami_name` fields. |
| `sp-cli:plugin:{spec_id}.launch-requested` emitted with new payload | NOT in compute-view | compute-view emits `sp-cli:node.launched` + `sp-cli:launch.success` directly. The per-spec event fires only from the OLD launcher-pane flow. |
| `sp-cli:ami.bake.started` event on BAKE_AMI | MISSING | n/a |
| BV2.5 supplies `EC2__Platform.create_node`; launch end-to-end | DONE backend-side; the FE-side narrowed scope to FRESH only |

**Project-rule violations:**

- `INSTANCE_TYPES` and `REGIONS` are still hardcoded constants at the top of `compute-view.js:13-15` and `launch-form.js:3-5`. After FV2.3 the catalogue is the source of truth — instance lists should at minimum come from the spec manifest's recommended sizes, not a frontend constant.
- `MAX_HOURS = [1,2,4,8,12,24]` likewise hardcoded.

**Integration concerns:**

- Two launch flows coexist (compute-view's `/api/nodes` and launch-panel's `entry.create_endpoint_path`). The launch-panel sends `stack_name` + `public_ingress` + `caller_ip: ''`; the compute-view sends `node_name`. These two payload shapes both need backend support and create test-surface duplication.
- The commit message admits scope reduction: "Removed public_ingress / Open access checkbox (no field in `Schema__Node__Create__Request__Base`)." This kills a real operator capability with no follow-up brief.
- `default_region` / `default_instance_type` defaults are read from the catalogue entry in launch-form (`:57-59`) but compute-view ignores those and reads from `settings-bus` defaults — two sources of defaults.

**Bad decisions / shortcuts:**

- The phase silently scoped down to "minimum FRESH-only path that unblocks BV2.5" without filing a follow-up brief for BAKE_AMI / FROM_AMI / AMI picker / cost preview. The debrief mentions this but no FV2.5b / FV2.5c is registered in `team/comms/briefs/`.
- Debrief text claims "FRESH-only acceptable for v0.2.x" — that contradicts the brief's explicit acceptance criteria ("Form renders the three-mode selector").

**Verdict:** Blocking issues for the brief as written. The phase delivered ~25% of the scope. The actual deliverable (FRESH-only launch via `/api/nodes`) works but is incorrectly tagged as "FV2.5 done".

---

## FV2.6 — Per-spec UI co-location at `sg_compute_specs/<name>/ui/`

**Commits:** `c4b2300 phase-FV2.6 (docker pilot)` + `2750409 phase-FV2.6 (all specs)` + `603eda3 phase-BV2.19 StaticFiles mount`

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| FV2.12 ran BEFORE FV2.6 | DONE | git log: FV2.12 merged at 08:38, BV2.19 at 09:08, FV2.6 docker at 09:44, FV2.6 all at 09:51. Order honoured. |
| `StaticFiles` mount via `app.mount(...)` per spec | DONE | `Fast_API__Compute.py:78-89`, iterates `registry.spec_ids()`, mounts at `/api/specs/{spec_id}/ui` |
| `IFD versioning` retained (`v0/v0.1/v0.1.0/`) | DONE | All 8 specs have `ui/{card,detail}/v0/v0.1/v0.1.0/` |
| 8 specs migrated (docker + 7) | DONE | `sg_compute_specs/{docker,podman,vnc,neko,prometheus,opensearch,elastic,firefox}/ui/{card,detail}/` all present; `api_site/plugins/` deleted; `api_site/components/sp-cli/sg-compute-<spec>-detail/` all deleted |
| `admin/index.html` loads from `/api/specs/<id>/ui/...` | DONE | `index.html:37-54` — all 16 spec script tags now use `/api/specs/<id>/ui/...` |
| Each spec carries `card/` + `detail/` substructure | DONE | listing confirms |
| Reality doc updated | DONE per commit message |

**Project-rule violations:**

- **All 7 non-docker specs migrated in a single commit** (`2750409`). The brief mandates "one spec per session" / "Don't try to do all 12 in one PR" (Goal section). This was violated wholesale; only the docker pilot followed the per-spec discipline.
- Co-located detail JS files use absolute imports like `/ui/shared/api-client.js`, `/ui/components/sp-cli/_shared/...` (`firefox-detail.js:2-9`). These work *only* when the dashboard is served from the legacy SP-CLI mount that exposes `/ui/`. After BV2.10 folded SP-CLI under `/legacy/`, those absolute paths now resolve to `/ui/...` which is no longer mounted at root in `Fast_API__Compute`. The dashboard is reachable at `/legacy/ui/admin/index.html`, but the spec-detail JS its `<script>` tags load (from `/api/specs/<id>/ui/...`) imports `/ui/shared/...` which 404s. **Likely a runtime breakage.**
- The `ollama`, `mitmproxy`, `open_design`, `playwright` specs in `sg_compute_specs/` have no `ui/` folder — `_mount_spec_ui_static_files` correctly skips them (`Spec__UI__Resolver` returns `None`), but the catalogue will list them as launchable yet they have no card. Silent gap.

**Integration concerns:**

- **Absolute `/ui/` imports vs legacy mount move.** This is the most serious concrete bug from the FV2 work. Either the imports need to change to `/legacy/ui/...` or `Fast_API__Compute` needs to also mount the dashboard StaticFiles at `/ui/` (or the dashboard needs to be served at root again). No regression test covers cross-mount asset loading.
- **No catalogue field for `ui/` presence.** The catalogue doesn't tell the frontend whether a spec ships UI assets, so admin.js / specs-view can't degrade gracefully. The script tags in `admin/index.html` are still hand-maintained — co-location moved the *files*, not the *registration*.

**Bad decisions / shortcuts:**

- Doing 7 specs in one shot with a sed-rewrite (per commit message: "two sed rules"). Sed rewrites of import paths bypass per-spec testing of the migration. None of the migrated detail components were exercised post-move beyond the docker pilot.
- `Schema__Spec__Manifest` (catalogue entry) gained no field describing UI presence/version/asset paths — a missed opportunity that would have made the script-tag list catalogue-driven.

**Verdict:** Has issues / borderline blocking. The mechanics (move + StaticFiles mount) shipped, but the absolute-`/ui/`-import problem is a likely runtime break post-BV2.10, and the "one spec per session" discipline was abandoned.

---

# Top 5 frontend issues across all 6 phases (severity-ordered)

1. **`/ui/...` absolute imports in co-located spec detail JS (FV2.6)** — files like `sg_compute_specs/firefox/ui/detail/.../sg-compute-firefox-detail.js:2-9` import from `/ui/shared/api-client.js` and `/ui/components/sp-cli/_shared/...`. After BV2.10 folded SP-CLI under `/legacy/`, the `/ui/` namespace is no longer mounted by `Fast_API__Compute`. Detail panels almost certainly 404 on import. Highest priority — likely a live runtime break.

2. **FV2.5 silently scoped down to FRESH-only** — three-mode selector, AMI picker, BAKE_AMI cost preview, FROM_AMI validation: all absent. Brief acceptance criteria explicitly require these. No follow-up FV2.5b brief filed. Compounding: `INSTANCE_TYPES` / `REGIONS` / `MAX_HOURS` remain hardcoded constants in two places (`compute-view.js:13-15`, `launch-form.js:3-5`) instead of being catalogue-driven.

3. **Two parallel launch flows with two payload shapes** — `sg-compute-compute-view._launch()` POSTs `/api/nodes` with `{spec_id, node_name, ...}` (FV2.5); `sg-compute-launch-panel._launch()` POSTs `entry.create_endpoint_path` with `{stack_name, public_ingress, caller_ip: '', ...}` (legacy). The Specs-view "Launch node" button (FV2.4) routes to the legacy panel via `sp-cli:catalog-launch`, so FV2.4's main CTA bypasses FV2.5's new path. Field-name confusion (`stack_name` vs `node_name`, `type_id` vs `spec_id`) is encoded into 6 fallback `||` reads in `admin.js`.

4. **`user/user.js` was never migrated (FV2.2 scope gap)** — lines 76-77 still call `/catalog/types` and `/catalog/stacks` unconditionally with no `useLegacyApiBase` toggle. The brief verified the admin path only. The user dashboard breaks the moment legacy URLs disappear from the control plane.

5. **`<sp-cli-spec-detail>` (FV2.4 Task 3) silently dropped** — the spec card has no "View detail" link, no manifest panel, no `extends` lineage placeholder, no AMI list, no README link. Brief required all of these. Not flagged in the debrief as deferred.

---

# Cross-cutting rule-violation patterns

- **Hardcoded constants instead of catalogue/manifest fields:** `INSTANCE_TYPES`, `REGIONS`, `MAX_HOURS`, `COST_TABLE`, `WORDS`, `NAME_WORDS` in `compute-view.js` and `launch-form.js`. These should come from `Schema__Spec__Manifest__Entry` (recommended sizes per spec) and a spec-defined cost table.
- **Static `<script>` tags in `admin/index.html` (8 cards + 8 details) are still the de-facto registry.** Catalogue is the data source; HTML is the rendering source. FV2.3 acknowledged this in a comment (`index.html:31-35`) but did not solve it.
- **Silent error swallowing**: `loadCatalogue().catch(err => console.warn(...))` (`admin.js:47`); `getCatalogue()` callers wrap in `try { ... } catch (_) { return }` (specs-view, compute-view). Network failures = blank UI, no user signal.
- **Compat-event proliferation in `admin.js`:** 8 deprecated event names retained side-by-side with new names (lines 69-74, 109-110, 113-114, 137-148). Necessary during transition but should carry an expiry phase.

---

# Phases that need rework (prioritised)

1. **FV2.6 — fix `/ui/` absolute imports** before any further StaticFiles work; add a regression test that loads each `<spec>-detail.js` end-to-end through the StaticFiles mount.
2. **FV2.5 — file follow-up brief(s)** for BAKE_AMI / FROM_AMI / AMI picker / cost preview / mode selector. Mark FV2.5 as PARTIAL in the debrief index.
3. **FV2.4 — build `<sg-compute-spec-detail>`** as required by the brief, and re-route the Specs-view Launch button through the FV2.5 generic flow rather than the legacy launch-panel.
