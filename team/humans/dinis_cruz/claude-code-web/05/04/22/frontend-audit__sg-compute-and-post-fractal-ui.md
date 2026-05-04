# Frontend Audit — SG/Compute Migration Plan + Post-Fractal-UI Cleanup Brief

**Date:** 2026-05-04 (UTC 22)
**Auditor:** explorer agent
**Branch:** `dev` @ `v0.1.169` (HEAD `5483738`)
**Briefs audited:**
- `team/comms/briefs/v0.1.140__sg-compute__migration/20__frontend-plan.md` (F1..F10)
- `team/comms/briefs/v0.1.140__post-fractal-ui__frontend/01..05`

Status legend: ✅ DONE · ⚠ PARTIAL · ❌ NOT DONE · DEFERRED (explicit in brief)

---

## Part A — SG/Compute frontend plan (F1..F10)

| Item | Status | Evidence (file:line) | Notes |
|------|--------|----------------------|-------|
| **F1** Terminology label sweep | ✅ | tag `phase-F1__terminology-labels` (commit `7b6282a`); `sp-cli-launcher-pane.html:3` ("Launch a node"); `sp-cli-stacks-pane.html:4` ("Active Nodes"); `sp-cli-launch-form.html:3` ("Node name"); `sp-cli-launch-panel.html:4,15` ("Launch node"); `sp-cli-events-log.html:5` ("Nodes"); `sp-cli-top-bar.html:3` ("SG/Compute"); `sp-cli-left-nav.html:5,9,13,18,23` (Compute / Nodes / Stacks / Settings / API); `admin.js:27` (VIEW_TITLES uses Active Nodes / Stacks). Settings-view contains zero "Plugin" labels. | One residual user-facing string: `sp-cli-launch-panel.js:46` `"Stack name is required."`. Comments / variable names ("Plugin / settings events", `_mainStackId`) remain by design — F1 explicitly excludes them. "Stack" labels in `sp-cli-stacks-view.html` and `sp-cli-left-nav.html:15` are the *new* multi-node Stacks meaning (F7), which is the post-rename vocabulary. |
| **F2** API client migration (`/api/{nodes,specs,pods,stacks}` + `useLegacyApiBase` flag) | ❌ | `shared/api-client.js` is a generic `apiClient` with no base-path switch (entire file ~50 lines, no `useLegacyApiBase`). Callers still use legacy paths: `admin/admin.js:257-258` (`/catalog/types`, `/catalog/stacks`); `user/user.js:76-77`; `shared/catalog.js:12` (`/catalog/types`); `admin.js:154` (`/${type_id}/stack/${name}`). | No `useLegacyApiBase` toggle in `shared/settings-bus.js`. New `/api/{specs,nodes,pods,stacks}` URLs not adopted. Field renames (`stack_id`→`node_id`, `type_id`→`spec_id`, `container_count`→`pod_count`) not done — `stack_name`, `type_id`, `stack_info` still pervasive. Blocked-by note in plan calls out backend phase 4; backend control-plane state unverified by this audit. |
| **F3** Specs view (left-nav item + browse pane) | ❌ | No `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-specs-view/` directory. `sp-cli-left-nav.html` lists Compute / Nodes / Stacks / Settings / API — no "Specs" item. | Spec catalogue is hard-coded inside `sp-cli-compute-view.js:6-…` (the comment literally says "Spec catalogue (static until backend phase B4 ships /api/specs)"). |
| **F4** Wire-event vocabulary `stack.*`→`node.*` | ✅ | New emitters: `sp-cli-launch-panel.js:64` (`sp-cli:node.launched`); `sp-cli-stacks-pane.js:81` (`sp-cli:node.selected`); `sp-cli-compute-view.js:187` (`sp-cli:node.launched`). Listeners: `admin.js:64-65,107` (node.selected / node.deleted / node.launched). Back-compat aliases: `admin.js:67-72` (DEPRECATED comments); `sp-cli-stacks-pane.js:82-83` dispatches both forms; `sp-cli-events-log.js:20-23,44-46` lists both ACTIVE and DEPRECATED. | Per-spec event rename (`sp-cli:plugin:firefox.*` → `sp-cli:spec:firefox.*`) NOT done — `admin.js:102` still listens on `sp-cli:plugin:${t}.launch-requested`; `sp-cli-events-log.js:51` still tracks `sp-cli:plugin.toggled`. **F4 partial — entity names migrated, "plugin" → "spec" namespace inside per-type events is not.** Mark ⚠ on the per-type half. |
| **F5** Catalogue loader (`shared/spec-catalogue.js`, drop `PLUGIN_ORDER`) | ❌ | No `shared/spec-catalogue.js`. `sp-cli-launcher-pane.js:4,30` still defines and iterates `const PLUGIN_ORDER = [...]`. `getAllPluginToggles()` still imported (`sp-cli-launcher-pane.js:2`). `admin/admin.js` uses static `LAUNCH_TYPES`. | The static catalogue moved into `sp-cli-compute-view.js` (a new central object) — that is closer to the goal but is not the manifest-driven flow the brief calls for. No `sp-cli:catalogue.loaded` emitter. |
| **F6** Per-spec UI co-location at `sg_compute_specs/<name>/ui/` | ❌ | `find sg_compute_specs -type d -name ui` returns nothing. All per-spec UI still under `sgraph_ai_service_playwright__api_site/plugins/{name}/` and `components/sp-cli/sp-cli-{name}-detail/`. | Plugin folders unchanged: `plugins/{docker,elastic,firefox,neko,opensearch,podman,prometheus,vnc}` all present. |
| **F7** Stacks placeholder view | ✅ | `components/sp-cli/sp-cli-stacks-view/v0/v0.1/v0.1.0/sp-cli-stacks-view.html` exists with "Coming soon" card; `sp-cli-left-nav.html:13-16` wires `data-view="stacks"`; `admin.js:27` adds it to VIEW_TITLES. | Distinct from `sp-cli-stacks-pane` (active-nodes list). Matches brief intent. |
| **F8** Host-plane URL update (`/containers/*` → `/pods/*`) | ⚠ | `sp-cli-nodes-view.js:353` (`${base}/pods/list`); `:433` (`/pods/{name}/stats`); `:457,602` (`/pods/{name}/logs`). Sidecar already on `/pods/*` per commit `bf13d62` ("nodes-view: sync with B6 containers→pods rename"). | Not a per-brief PR; landed via the host-control-plane / sidecar work. No remaining `/containers/` reference in `nodes-view.js`. UI label sweep (any "Container" copy) not separately verified — but the relevant tab is now "Pods/Nodes" idiomatic. |
| **F9** `sp-cli-*` → `sg-compute-*` cosmetic prefix rename | DEFERRED | All 30+ web components under `components/sp-cli/sp-cli-*` retain the old prefix; `customElements.define('sp-cli-...', …)` everywhere. Brief itself states deferred pending F1-F8. | Expected. No work yet. |
| **F10** Move dashboard to `sg_compute/frontend/` | DEFERRED | `sg_compute/` exists with `cli/`, `core/`, `host_plane/`, `control_plane/`, `platforms/`, `primitives/`, `brief/` — **no `frontend/` subfolder**. Dashboard still at `sgraph_ai_service_playwright__api_site/`. | Brief flags this as may-slip-into-separate-brief. |

---

## Part B — Post-Fractal-UI frontend brief (01..05)

| Item | Status | Evidence (file:line) | Notes |
|------|--------|----------------------|-------|
| **01** Plugin manifest loader (drop 4-place duplication) | ❌ | Same as F5: `shared/plugin-manifest.js` does not exist; `sp-cli-launcher-pane.js:4` still has `PLUGIN_ORDER`; `shared/settings-bus.js` still owns `DEFAULTS`; `admin/admin.js` still has static `LAUNCH_TYPES`. | Backend-blocked per the brief; status here mirrors F5. |
| **02** Launch flow — three creation modes (FRESH/BAKE_AMI/FROM_AMI) | ❌ | `sp-cli-launch-form.html` shows Region / Instance type / Auto-stop only — no creation-mode radio, no AMI picker, no timeout-minutes. Grep `creation_mode\|FRESH\|BAKE_AMI\|FROM_AMI` returns zero hits across `sgraph_ai_service_playwright__api_site/`. No `sp-cli-ami-picker` component. | Backend-blocked. Submit payload at `sp-cli-launch-form.js:72` is still `{ stack_name, region, instance_size, auto_stop_after_hours, open_access }`. |
| **03** Firefox configuration column (5 sub-panels) | ❌ | `sp-cli-firefox-detail.html` has Info / Terminal / Host API tabs only (single-column). No `sp-cli-firefox-credentials/`, `sp-cli-firefox-mitm/`, `sp-cli-firefox-security/`, `sp-cli-firefox-profile/`, `sp-cli-firefox-instance/` directories exist (find returns empty). No `_shared/sp-cli-vault-blob-picker/` and no `_shared/sp-cli-health-badge/`. | Backend-blocked. The detail did absorb the host-control-plane Terminal + Host API tabs from a different brief. |
| **04.1** linux→podman rename residue | ✅ | No `plugins/linux/` directory. No `sp-cli-linux-detail/` directory. `shared/settings-bus.js` has zero `linux` refs. `_shared/sp-cli-stack-header`, `sp-cli-stacks-pane`, `sp-cli-user-pane` show no `type-linux` / `linux:` map entries. `sp-cli-launch-form.html:3` placeholder example is `podman-nova-4217`. | The 9 listed sites all swept. |
| **04.2** Remove deprecated components (`sp-cli-vnc-viewer`, `sp-cli-launch-modal`, `sp-cli-stack-detail`, `sp-cli-vault-activity`) | ✅ | `find … -name "*vnc-viewer*" -o -name "*launch-modal*" -o -name "*stack-detail*" -o -name "*vault-activity*"` returns empty. | All four deleted. |
| **04.3** Embed `<sg-remote-browser>` in elastic / prometheus / opensearch detail | ✅ | `sp-cli-elastic-detail.html:12`, `sp-cli-prometheus-detail.html:6`, `sp-cli-opensearch-detail.html:6` all render `<sg-remote-browser provider="iframe">`; matching `.js` imports the component; `.css` styles the `.browser-section sg-remote-browser`. | Done. |
| **04.4** Card label vs provider consistency (firefox) | ⚠ | Not separately verified in this audit — the `plugins/firefox/v0/v0.1/v0.1.0/sp-cli-firefox-card.js:3` `display_name` was not opened. Treat as low-impact. | Should be cheap to verify in a follow-up. |
| **04.5** Plugin-folder structure decision (note) | ❌ | No decision file at `team/roles/ui-architect/decisions/` — the role folder still does not exist. | Documentation-only item, not actioned. |
| **05.1** Out-of-brief plugin: firefox (ratify) | ❌ | No reality-doc UI fragment update located; no UI Architect decision note. Firefox plugin remains shipped without explicit ratification. | Decision-only. |
| **05.2** Out-of-brief navigation: api view (ratify) | ❌ | API view lives at `sp-cli-api-view/v0/v0.1/v0.1.0/`, wired from `sp-cli-left-nav.html:23-26`. No formal ratification note found. | Decision-only. |
| **05.3** Reserved-but-unimplemented events | ❌ | No spec published; reserved-list maintenance not visible in `sp-cli-events-log.js`. | Decision-only. |
| **05.4** Publish event vocabulary as a spec | ❌ | No `library/docs/specs/v*__ui-event-vocabulary.md`; grep returns no hits. The `FAMILIES` map in `sp-cli-events-log.js:14-30` remains the implicit source. | Should be cheap once F4 is fully landed. |
| **05.5** UI-panel re-show UX | ❌ | Not investigated — `sp-cli-settings-view.js:120-123` still drives a reset-layout button per the HTML. | Open. |
| **05.6** Vault-optional flow | ❌ | Not investigated. | Open. |

---

## Part C — Out-of-scope additions (built outside the two source briefs)

These are present on `dev` but were authorised by **other** briefs that emerged after the two source briefs were written.

| Surprise | Where | Authorising brief |
|----------|-------|-------------------|
| Host shell (`sp-cli-host-shell` web component, Terminal tab on every detail) | `components/sp-cli/_shared/sp-cli-host-shell/` | `team/comms/briefs/v0.1.140__host-control-plane-ui/` ("Terminal tab — run allowlisted shell commands on the EC2 host") |
| Host API panel with iframe SwaggerUI (`sp-cli-host-api-panel`, Host API tab on every detail) | `components/sp-cli/_shared/sp-cli-host-api-panel/` | Same brief: "Host API tab — Swagger iframe for the instance's own FastAPI control plane at `{host_api_url}/docs`" |
| `sp-cli-nodes-view` (active-nodes view with Boot Log + EC2 Info tabs, host-API-key reveal/copy, sidecar polling on `:19009`, `/pods/*` endpoints) | `components/sp-cli/sp-cli-nodes-view/` | Group A features (commit `033ef85` "Group A features (A1–A4)"); Boot Log tab (commit `c3e8ffd`); host-API-key reveal (commit `8caf598`); EC2 Info tab (commit `6f14da1`). Authorised by `v0.1.154__sidecar-enhancements-for-ui/` and the host-control-plane-ui brief. |
| Sidecar wiring (cookie-based auth, CORS, `/docs-auth`, iframe terminal) | `sp-cli-host-api-panel`, `sp-cli-host-shell`, sidecar at `:19009` | `team/comms/briefs/v0.1.154__sidecar-cors-and-docs-auth/`; `v0.1.154__sidecar-enhancements-for-ui/`; `v0.1.154__ws-shell-stream-auth/` |
| Docker sidecar + node list/create/delete CLI (commit `8319ffa`, "Phase 3/5") | `sgraph_ai_service_playwright__cli`, host plane | Host control plane brief / sidecar enhancements |
| Diagnostics storage viewer (`sp-cli-storage-viewer`) | `components/sp-cli/sp-cli-storage-viewer/` | Commit `0a15d0d` ("diagnostics: add storage viewer pane") — appears unbriefed (housekeeping). |
| Resizable/collapsible nodes-view list pane + redesigned stop button (commit `15dbc47`) | `sp-cli-nodes-view` | Sidecar / host-control-plane work — incidental UX polish. |
| `ec2-info` move from sidecar to SP CLI catalog (commit `1c96fbe`) | `sp-cli-nodes-view.js:511` calls `/catalog/ec2-info` | IAM scoping fix. Authorised by sidecar series. |
| Memory-FS / S3 storage node spec | brief only (`team/comms/briefs/v0.1.162__s3-storage-node/`) — no `sg_compute_specs/s3_server/` shipped yet | `v0.1.162__s3-storage-node` (still PROPOSED) — UI work has not started. |

---

## Gaps (work that the briefs called for and was not done)

1. **F2 API-client migration not started.** `shared/api-client.js` has no `/api/...` base, no `useLegacyApiBase`, no `node_id`/`spec_id` field renames. The dashboard still calls legacy `/catalog/types`, `/catalog/stacks`, `/{type}/stack/{name}` paths.
2. **F3 Specs view not started.** No `sp-cli-specs-view`, no left-nav item, no `GET /api/specs` consumer.
3. **F4 only half done.** Entity events (`stack.*`→`node.*`) migrated and aliased correctly. Per-type namespace (`sp-cli:plugin:{type}.*` → `sp-cli:spec:{type}.*`) NOT migrated — emitters and `admin.js:102` still on `plugin:`.
4. **F5 / Post-fractal item 01 (manifest loader) not started.** `PLUGIN_ORDER` literal still present at `sp-cli-launcher-pane.js:4`. The compute-view static catalogue object at `sp-cli-compute-view.js:6` is a step sideways, not the manifest-driven loader.
5. **F6 per-spec UI co-location not started.** No `sg_compute_specs/<name>/ui/` directories.
6. **Post-fractal item 02 (three creation modes) not started.** Launch form has neither mode selector nor AMI picker. No timeout-minutes field.
7. **Post-fractal item 03 (firefox 5 sub-panels) not started.** Firefox detail still single-column with Info/Terminal/Host-API tabs only. No `sp-cli-vault-blob-picker` shared widget. No `sp-cli-health-badge` shared widget.
8. **Post-fractal item 04.4 / 04.5** — decision documents not filed (UI Architect decisions folder still does not exist).
9. **Post-fractal item 05.4** — event-vocabulary spec under `library/docs/specs/` has not been published.

The gaps are clustered into two backlog buckets:
- **Backend-blocked** (F2, F3, F5, F6, items 01/02/03 in post-fractal). These wait on the SG/Compute control-plane (`/api/specs`, `/api/nodes`, three-mode launch payload, firefox config endpoints, vault writes).
- **Frontend-only** (F4 per-type namespace, items 04.4 / 04.5, item 05.4) — could land any time; no excuse to delay.

---

## Out-of-scope additions — assessment

The largest body of frontend work shipped on `dev` since v0.1.140 belongs to **the host-control-plane / sidecar / nodes-view track**, not to either of the two source briefs. That work is authorised by a real chain of briefs:

- `v0.1.140__host-control-plane-ui/` — Terminal + Host API tabs.
- `v0.1.154__sidecar-cors-and-docs-auth/` — CORS + docs-auth.
- `v0.1.154__sidecar-enhancements-for-ui/` — boot log, container logs, live stats.
- `v0.1.154__ws-shell-stream-auth/` — WS shell stream auth.

Nothing in this audit looks like *un*-authorised feature creep. The two anomalies worth a note are:

- **Diagnostics storage viewer** (commit `0a15d0d`) appears to be a small ad-hoc convenience. Not blocked-on a brief.
- **Group A features (A1-A4)** in commit `033ef85` are described as part of the same nodes-view track but the "Group A" naming does not match a specific brief filename — this is internal session shorthand. Authorisation is implicit via the host-control-plane / sidecar series.

---

## New briefs that emerged (post-source-briefs timeline)

1. `team/comms/briefs/v0.1.140__host-control-plane-ui/` — Terminal + Host API tabs.
2. `team/comms/briefs/v0.1.154__sidecar-cors-and-docs-auth/` — sidecar CORS / `/docs-auth`.
3. `team/comms/briefs/v0.1.154__sidecar-enhancements-for-ui/` — boot log + container logs + stats.
4. `team/comms/briefs/v0.1.154__ws-shell-stream-auth/` — WS shell auth.
5. `team/comms/briefs/v0.1.162__s3-storage-node/` — proposed S3 storage node spec (frontend not yet started).

---

## One-line summary

**SG/Compute frontend plan F1..F10:** F1 ✅, F2 ❌, F3 ❌, F4 ⚠ (entity events done, per-type namespace not), F5 ❌, F6 ❌, F7 ✅, F8 ✅, F9 DEFERRED, F10 DEFERRED.
**Post-fractal-UI items 01..05:** 01 ❌, 02 ❌, 03 ❌, 04.1 ✅, 04.2 ✅, 04.3 ✅, 04.4 ⚠ (not verified), 04.5 ❌, 05.1-05.6 ❌ (decision-only items, none filed).

The shipped work since v0.1.140 is dominated by the host-control-plane / sidecar / nodes-view track — authorised by a chain of new briefs (`v0.1.140__host-control-plane-ui`, `v0.1.154__sidecar-*`), not by the two source briefs being audited here.
