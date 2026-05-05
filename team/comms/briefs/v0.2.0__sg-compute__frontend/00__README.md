# v0.2.x — Frontend (FV2.x phases)

**Audience:** the frontend Sonnet team
**Prerequisites:** read [`../v0.2.0__sg-compute__architecture/`](../v0.2.0__sg-compute__architecture/) in full first (00 → 01 → 02 → 03).

This folder is a **per-phase brief**. Each `FV2_NN__*.md` file is self-contained: read it, do it, ship one PR, move on. **One phase per PR. One PR per session.**

Branch naming: `claude/fv2-{N}-{description}-{session-id}`.
PR title: `phase-FV2.{N}: {short summary}`.

---

## Phase index (recommended order)

| # | File | Theme | Blocked by |
|---|------|-------|------------|
| FV2.1 | [`FV2_1__state-vocabulary-fix.md`](FV2_1__state-vocabulary-fix.md) | Centralise node-state vocabulary; fix 6 `'running'` hardcodes in `sp-cli-nodes-view.js` | — |
| FV2.2 | [`FV2_2__api-client-migration.md`](FV2_2__api-client-migration.md) | Switch dashboard to `/api/specs`, `/api/nodes`; field renames; feature flag | — |
| FV2.3 | [`FV2_3__catalogue-loader.md`](FV2_3__catalogue-loader.md) | `shared/spec-catalogue.js`; delete `PLUGIN_ORDER`, `CATALOG`, `LAUNCH_TYPES`, `DEFAULTS.plugins` | FV2.2 |
| FV2.4 | [`FV2_4__specs-view.md`](FV2_4__specs-view.md) | Specs left-nav item + `<sp-cli-specs-view>` | FV2.3 |
| FV2.5 | [`FV2_5__launch-flow-three-modes.md`](FV2_5__launch-flow-three-modes.md) | Launch form with creation-mode selector + AMI picker + size + timeout | BV2.5 |
| FV2.7 | [`FV2_7__pods-tab-unified-url.md`](FV2_7__pods-tab-unified-url.md) | Switch Pods tab from `{host_api_url}/pods/list` to `/api/nodes/{id}/pods/list` | BV2.3 |
| FV2.8 | [`FV2_8__pods-url-update.md`](FV2_8__pods-url-update.md) | Confirm zero `/containers/*` URL references in dashboard | After FV2.7 |
| FV2.9 | [`FV2_9__event-vocabulary-finish.md`](FV2_9__event-vocabulary-finish.md) | Migrate `sp-cli:plugin:*` → `sp-cli:spec:*`; publish event vocabulary spec | — |
| FV2.10 | [`FV2_10__a11y-pass.md`](FV2_10__a11y-pass.md) | A11y on `sp-cli-nodes-view` tabs + icon buttons + spec cards | — |
| FV2.11 | [`FV2_11__delete-legacy-components.md`](FV2_11__delete-legacy-components.md) | Delete `sp-cli-stacks-pane`, unused `shared/catalog.js`, `api.ipify.org` external call | After FV2.4 |
| FV2.12 | [`FV2_12__cosmetic-rename.md`](FV2_12__cosmetic-rename.md) | `sp-cli-*` → `sg-compute-*` cosmetic web-component prefix rename | After FV2.9 ✅ — **un-deferred, blocks FV2.6** |
| FV2.6 | [`FV2_6__per-spec-ui-co-location.md`](FV2_6__per-spec-ui-co-location.md) | Move per-spec card + detail UI into `sg_compute_specs/<name>/ui/`; `StaticFiles` mount | After FV2.12 + BV2.x (StaticFiles mount) |
| FV2.13 | [`FV2_13__dashboard-move.md`](FV2_13__dashboard-move.md) | Move dashboard to `sg_compute/frontend/` (deferred to v0.3, doc-only here) | After FV2.12 |

---

## Phase ordering rationale

- **FV2.1** is unblocked and high-value — fixes a latent bug. Run first.
- **FV2.2** unblocks FV2.3, FV2.4, FV2.7 (the API-client migration is the foundation).
- **FV2.3** kills the four hardcoded plugin lists in one shot — biggest cleanup win.
- **FV2.5** waits on BV2.5 (`POST /api/nodes` + `EC2__Platform.create_node`).
- **FV2.7** waits on BV2.3 (`Pod__Manager` + `Routes__Compute__Pods`).
- **FV2.9-FV2.10** are quality bars — run when capacity allows.
- **FV2.11** cleans up after the new path is established.
- **FV2.12** is un-deferred (2026-05-05 Architect decision): must run before FV2.6 so co-located files land with final `sg-compute-*` names. Blocked by FV2.9 only — which is done.
- **FV2.6** now runs after FV2.12 (not FV2.3 as originally planned). Also needs a backend BV2.x slice: `StaticFiles` mount in `Fast_API__Compute` serving `sg_compute_specs/<id>/ui/` at `/api/specs/<id>/ui/`. UI assets served via CF+S3 / `tools.sgraph.ai` in production (same static-file convention).
- **FV2.13** remains deferred to v0.3.

---

## Cross-cutting frontend rules (binding every phase)

- **No build toolchain.** Native ES modules. Plain CSS. Web Components with Shadow DOM.
- **Three-file pattern**: `.js` + `.html` + `.css` siblings under `{name}/v0/v0.1/v0.1.0/`.
- **Custom-element naming**: until FV2.12, keep `sp-cli-*`. New components added during FV2.x may use either prefix; recommend `sp-cli-*` for now to keep FV2.12's scope smaller.
- **Events on `document`** with `{ bubbles: true, composed: true }`.
- **Accessibility**: WCAG AA contrast, keyboard navigation, ARIA labels on icon-only controls.
- **No emoji** in source files unless existing convention uses them (plugin card icons stay).
- **Branch:** `claude/fv2-{N}-{description}-{session-id}`.
- **PR title**: `phase-FV2.{N}: {short summary}`.
- **CLAUDE.md rule 9 (no underscore-prefix)** is **Python only**. JS files keep `_foo()` convention.

---

## When you start a session

1. `git fetch origin dev && git merge origin/dev`.
2. Read this README; pick the next un-shipped phase.
3. Open the phase file.
4. Verify the "Blocked by" relationships in the index — back-end phases must have shipped first where listed.
5. Open a feature branch; ship the phase; debrief.
