# UI Architect — Pass 2: Scope statement, 05/01 brief implications, boundary risks

**Date:** 2026-05-01
**Version:** v0.1.140
**Branch:** `claude/ui-architect-agent-Cg0kG`
**Scope:** Pass 2 of 2. UI Architect role scope statement, the three 05/01 briefs translated into UI implications, and boundary risks. Pass 1 (sibling agent) covers the existing UI tour, recently merged UI commits, patterns/boundaries, and the 04/29 brief audit; this document does not duplicate that work and references it where relevant.

Pass 1 file (if present): `team/humans/dinis_cruz/claude-code-web/05/01/15/ui-architect__pass-1__code-and-implementation.md`

---

## 1. UI Architect — scope statement

The UI Architect owns the static-site dashboard and its component grammar. The backend Architect (`team/roles/architect/ROLE.md:6`) owns the FastAPI surface, `Type_Safe` schemas, the `Step__Executor`-only-touches-`page.*` rule, and the single-image / five-target deployment guarantee. The two roles meet at the HTTP boundary: the backend Architect specifies request and response shapes, and the UI Architect specifies how the dashboard consumes those shapes, what events the dashboard publishes between its own components, and how plugins extend the launcher and detail panels.

This split keeps the two surfaces from rotting into each other. The UI Architect can evolve component versioning (`v0/v0.1/v0.1.0/`), card/detail composition under `sp-cli/`, and the dashboard plugin folder under `sgraph_ai_service_playwright__api_site/plugins/` without dragging in route or schema work. Conversely, route or schema changes are rejected by the backend Architect at `team/roles/architect/ROLE.md:88` regardless of UI need.

**OWNED by UI Architect**

- The static-site dashboard tree under `sgraph_ai_service_playwright__api_site/`.
- The `sp-cli-*` web component family under `sgraph_ai_service_playwright__api_site/components/sp-cli/` (32 components observed at time of writing).
- The plugin / panel architecture under `sgraph_ai_service_playwright__api_site/plugins/` (folders: `docker`, `elastic`, `firefox`, `linux`, `neko`, `opensearch`, `podman`, `prometheus`, `vnc`).
- The dashboard event vocabulary (`sp-cli:plugin:<name>.launch-requested`, `sp-cli:stack.launched`, `sp-cli:settings.loaded`, `sp-cli:plugin.toggled`, the `FAMILIES` map at `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-events-log/v0/v0.1/v0.1.0/sp-cli-events-log.js:14`).
- Feature toggles via `getAllPluginToggles()` and the settings bus at `sgraph_ai_service_playwright__api_site/shared/settings-bus.js`.
- Component versioning (`vMAJOR/vMAJOR.MINOR/vMAJOR.MINOR.PATCH/`) and the fractal-UI direction described in the 28 Apr brief.
- The dashboard-side contract for consuming the API (URL shapes, expected JSON keys, error rendering).

**NOT owned by UI Architect**

- FastAPI routes, route classes, route catalogue (`library/docs/specs/v0.20.55__routes-catalogue-v2.md`).
- `Type_Safe` schemas, `Safe_*` primitives, `Enum__*` types (`library/docs/specs/v0.20.55__schema-catalogue-v2.md`).
- `Step__Executor` and the JS allowlist gate.
- AWS / Lambda / ECR / Docker image work, deploy-via-pytest, GitHub Actions.
- The Python service layer and any code under `sgraph_ai_service_playwright/`.

**Negotiated with the backend Architect**

- Plugin manifest / toggle JSON shape consumed by `getAllPluginToggles()`.
- The launch payload sent by `sp-cli-launch-modal` to backend stack endpoints (creation mode, AMI selector, instance size, timeout).
- Vault hand-off for per-instance credentials and MITM scripts (Firefox brief).
- Auth / API-key envelope for the host-FastAPI control plane (container-runtime brief).
- Event names that cross the wire (e.g. `stack.launched` echoes a backend transition).

---

## 2. 05/01 brief — Firefox browser plugin: UI implications

Brief: `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__firefox-browser-plugin.md`.

### 2.1 What's already shipped

- Card lives at `sgraph_ai_service_playwright__api_site/plugins/firefox/v0/v0.1/v0.1.0/sp-cli-firefox-card.js` (commit `c5566d2`). `STATIC = { type_id: 'firefox', display_name: 'Firefox (noVNC)', icon: '🦊', stability: 'experimental', boot: '~90s', soon: false, create_endpoint_path: '/firefox/stack' }` (line 3).
- Card emits `sp-cli:plugin:firefox.launch-requested` on click — `sgraph_ai_service_playwright__api_site/plugins/firefox/v0/v0.1/v0.1.0/sp-cli-firefox-card.js:26`.
- Detail component scaffolded at `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-firefox-detail/v0/v0.1/v0.1.0/` (commit `092f069`). `provider: 'iframe'` is wired at `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-firefox-detail/v0/v0.1/v0.1.0/sp-cli-firefox-detail.js:54`.
- Firefox is included in the launcher order at `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-launcher-pane/v0/v0.1/v0.1.0/sp-cli-launcher-pane.js:4` (last entry of `PLUGIN_ORDER`).

### 2.2 Still PROPOSED — does not exist yet

The brief lists a configuration column with five sub-panels (Configuration, MITM Proxy, Security, Firefox Settings, Instance). A grep for `MITM`, `credentials`, `username`, `password`, `intercept` across `sp-cli-firefox-detail/` returns nothing. The detail today is a noVNC-style iframe shell. **PROPOSED — does not exist yet:**

- Username / password field + "Update Credentials" action (brief lines 44-46).
- MITM Proxy panel with status indicator, intercept-script picker, "Upload Script", "Open Proxy UI" (brief lines 48-53).
- Security toggles: self-signed certs, SSL intercept (brief lines 55-58).
- Firefox Settings panel: start page, Load Profile (brief lines 60-62).
- Instance controls: Bake AMI, Stop, Health badge with drill-down (brief lines 64-66).
- Vault-backed persistence for credentials, MITM scripts, profile (brief lines 91-103). No vault-write surface exists in `sp-cli-firefox-detail` today.
- Health-check display (green / amber / red) for container-running, Firefox-process, MITM, network, login-page (brief lines 104-114). **PROPOSED — does not exist yet.**
- iframe vs Neko/noVNC fallback decision is still implicit; the card label says "noVNC" but the detail uses `provider: 'iframe'`.

### 2.3 Recommended UI sequencing

1. Lock the Firefox detail layout (split column) and publish the panel slots before wiring data — this is the contract that downstream panels (security, MITM, instance) will plug into.
2. Land the credentials sub-panel first; it forces the vault hand-off contract to be defined with the backend Architect.
3. Land MITM panel + script upload — biggest API surface, drives the contract for vault-backed binary uploads.
4. Land health badge — depends only on a polled `GET /firefox/health` shape and unblocks the same pattern for podman / elastic.
5. Land "Bake AMI" — should reuse the same pattern as the ephemeral-infra brief (see Section 3) so it is built once across plugins.
6. Resolve the iframe vs Neko fallback (card display name says noVNC, code uses iframe) — the brief argues iframe should work; align card label with reality.

---

## 3. 05/01 brief — Ephemeral infrastructure next phase: UI implications

Brief: `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__ephemeral-infra-next-phase.md`.

This brief is dev-targeted but is the largest single piece of work the UI Architect role inherits. Each feature lands as a UI section; status today:

| # | Brief feature | Component(s) impacted | Status | Evidence |
|---|---------------|-----------------------|--------|----------|
| 1 | Split Creation from Live Instances | `sp-cli-launcher-pane`, `sp-cli-active-sessions`, `sp-cli-launch-panel`, `sp-cli-stacks-pane` | PARTIAL | Launcher + active sessions + stacks panes already exist as separate components, but the brief's "Creation Section" with creation-mode selector does not. |
| 2 | Three creation modes (fresh / bake / from AMI) | `sp-cli-launch-modal` | PROPOSED — does not exist yet. | Modal at `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-launch-modal/v0/v0.1/v0.1.0/sp-cli-launch-modal.html` only takes `stack_name`. Grep for `bake|AMI|fresh|from_ami` in launch-modal returns nothing. |
| 3 | AMI management UI (list / bake / delete / set default) | New component (`sp-cli-ami-manager` or extension to `sp-cli-launch-panel`) | PROPOSED — does not exist yet. | No `ami` references in `sp-cli/`. |
| 4 | SG/Send vault-server instance type | New plugin folder `plugins/sg-vault/` | PROPOSED — does not exist yet. | No `sg-vault` folder in `sgraph_ai_service_playwright__api_site/plugins/`; `PLUGIN_ORDER` does not contain it (`sp-cli-launcher-pane.js:4`). |
| 5 | Docker container management inside instances (list, start, stop, logs, expose ports) | `sp-cli-docker-detail`, possibly new `sp-cli-container-manager` | PARTIAL | `sp-cli-docker-detail` exists; brief's "list containers / start / logs / expose ports" sub-panel — PROPOSED — does not exist yet. |
| 6 | Remote shell (Option A — API-based) | New component `sp-cli-shell` (or detail-embedded terminal) | PROPOSED — does not exist yet. | No shell / terminal component in `sp-cli/`. |
| 7 | Prometheus metrics inline display | `sp-cli-prometheus-detail`, plus health badges on every detail | PARTIAL | `sp-cli-prometheus-detail` exists (`sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-prometheus-detail/v0/v0.1/v0.1.0/sp-cli-prometheus-detail.js`). Inline `/metrics` polling on other detail panels — PROPOSED — does not exist yet. |
| 8 | Stacks (multi-instance bundles, one-click launch) | `sp-cli-stacks-pane`, `sp-cli-stack-detail` | PARTIAL | Stacks pane and stack detail exist; "stack JSON definition" launch flow — PROPOSED — does not exist yet. |
| 9 | Cost surface for AMI lifecycle (storage cost, bake cost) | `sp-cli-cost-tracker` | PROPOSED — does not exist yet. | Brief implies AMI costs need to surface; cost tracker today does not differentiate AMI vs instance cost. |
| 10 | Activity for AMI bake progress | `sp-cli-activity-pane` | PROPOSED — does not exist yet. | Activity pane currently records launch / stop, not bake progress. |

The biggest UI-Architect decision here is whether "Creation" and "Live Instances" become two sibling routes inside the dashboard or whether they remain panes within one layout. The brief diagram at lines 36-74 implies two distinct sections; current code keeps them as collapsible panes. This is a fractal-UI direction call and should land before any of features 2-10 to avoid rework.

---

## 4. 05/01 brief — Container runtime abstraction (linux→podman): UI implications

Brief: `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__container-runtime-abstraction.md`.

### 4.1 What landed in the UI tree

- Podman card: `sgraph_ai_service_playwright__api_site/plugins/podman/v0/v0.1/v0.1.0/sp-cli-podman-card.js` (commit `3f1b75d`). `type_id: 'podman'`, `display_name: 'Podman host'`, `boot: '~10min'`, `create_endpoint_path: '/podman/stack'` (line 3).
- Podman detail: `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-podman-detail/v0/v0.1/v0.1.0/`.
- Launch event: `sp-cli:plugin:podman.launch-requested` (`sp-cli-podman-card.js:26`).
- Launcher order updated: `podman` is second in `PLUGIN_ORDER` at `sp-cli-launcher-pane.js:4`. `linux` has been removed from that array.

### 4.2 Stale `linux` references the rename did not clean up

A grep for `linux` across `sgraph_ai_service_playwright__api_site/` (excluding `sp-cli-linux-detail/` itself) shows the rename was incomplete from the UI side:

| File:line | What | Action |
|-----------|------|--------|
| `sgraph_ai_service_playwright__api_site/shared/settings-bus.js:117` | `default_instance_types?.linux` reference | Remove or rename to `podman`. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-settings-view/v0/v0.1/v0.1.0/sp-cli-settings-view.js:11` | Settings entry `{ name: 'linux', icon: '🐧', label: 'Bare Linux', stability: 'stable', boot: '~60s' }` | Replace with `podman` entry (already in launcher order but missing from settings list). |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-user-pane/v0/v0.1/v0.1.0/sp-cli-user-pane.css:76` | `.type-linux` colour token | Add `.type-podman` token; decide whether to retain `.type-linux` for legacy stacks. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-stack-detail/v0/v0.1/v0.1.0/sp-cli-stack-detail.css:44` | `.type-linux` colour token | Same as above. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-stacks-pane/v0/v0.1/v0.1.0/sp-cli-stacks-pane.css:54` | `.type-linux` colour token | Same as above. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-stack-header/v0/v0.1/v0.1.0/sp-cli-stack-header.js:5` | `linux: '🐧'` icon map | Add `podman: '🦭'`; keep `linux` only if old stacks are still rendered. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-launch-form/v0/v0.1/v0.1.0/sp-cli-launch-form.html:4` | Placeholder `e.g. linux-nova-4217` | Update placeholder. |
| `sgraph_ai_service_playwright__api_site/plugins/linux/v0/v0.1/v0.1.0/*` | Whole `plugins/linux/` folder still on disk | Decide: delete (rename complete) or keep (back-compat). The card defines `sp-cli-linux-card` but `PLUGIN_ORDER` no longer includes it, so the card is effectively dead code. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-linux-detail/` | Detail still on disk | Same call as above — orphaned unless kept for legacy. |

### 4.3 Outstanding UI work the brief implies

- Surface "which runtime" (Docker / Podman / future K8s) on every container-bearing detail. Brief calls for `GET /host/runtime` (line 76); UI today does not display runtime.
- Host FastAPI control-plane UI: container list / start / stop / logs / shell / metrics. This overlaps with ephemeral-infra Features 5, 6 and 9 (container management, shell, prometheus). Single component family proposed: `sp-cli-host-control` with sub-panels.
- Sidecar attachment UI (MITM proxy / remote browser / desktop streaming) — brief lines 147-170. **PROPOSED — does not exist yet.** No sidecar UI component today.
- Long-running vs ephemeral container modes — UI needs a mode selector when launching a container. **PROPOSED — does not exist yet.**
- Privileged-container indicator: only the host FastAPI is privileged (brief lines 95-104). UI should label this clearly to keep the security boundary visible.

---

## 5. Boundary risks & open questions

| # | Title | Risk | Negotiate with |
|---|-------|------|----------------|
| 1 | Plugin manifest shape under expansion | Card `STATIC` blob (`type_id`, `display_name`, `icon`, `stability`, `boot`, `soon`, `create_endpoint_path`) is duplicated per card with no shared schema. After firefox + podman + the proposed `sg-vault` and `host-control`, the 8-type registry hits 10+; need a typed manifest. | Backend Architect, Librarian |
| 2 | `PLUGIN_ORDER` is hard-coded | `sp-cli-launcher-pane.js:4` lists plugin names by hand. New plugins require editing this array, which contradicts "adding a plugin requires no core changes" (container-runtime brief, AC #11). | Backend Architect (manifest contract), Dev (loader change) |
| 3 | Event vocabulary stability | `sp-cli:plugin:<name>.launch-requested` and `sp-cli:stack.launched` etc. are scattered across files; the `FAMILIES` map at `sp-cli-events-log.js:14` is the closest thing to a canonical list. No spec. Risk: events drift, debug pane misclassifies. | Librarian (publish vocab), Dev |
| 4 | Vault hand-off for plugin-specific secrets | Firefox brief requires per-session vault writes (credentials, MITM scripts). UI does not yet have a vault-write component or a contract for "write this blob to the session's vault". `sp-cli-vault-status` and `sp-cli-vault-picker` exist but are read-oriented. | Backend Architect, Dev |
| 5 | Vault-optional flow now that the gate is removed | Pass 1 should cover the recent removal of the vault gate. Risk: UI assumes a vault key for any session that wants persistence (Firefox profiles, MITM scripts, AMI metadata). Need an explicit "no-vault degraded mode" UX. | Backend Architect, Dev |
| 6 | Feature-toggle storage | `getAllPluginToggles()` reads from `settings-bus.js` (line 117 still references `linux`). Toggles are stored client-side; what happens to a toggle when the underlying plugin is removed (linux)? Is there a server-side source of truth? | Backend Architect |
| 7 | `linux` orphan removal | `plugins/linux/`, `sp-cli-linux-card`, `sp-cli-linux-detail`, and 7 other files still reference `linux` after the linux→podman rename. Risk: confusion, dead code, broken settings entries. | Dev (cleanup PR), Librarian (reality doc) |
| 8 | iframe vs Neko/noVNC contract for Firefox | Card label says "Firefox (noVNC)" but detail uses `provider: 'iframe'`. The brief argues for iframe with X-Frame-Options removed, with Neko as fallback. UI needs a single source-of-truth flag. | Backend Architect (does the container expose iframe-ready headers?), Dev |
| 9 | Creation-mode contract for `sp-cli-launch-modal` | Today launches a stack with only `stack_name`. Ephemeral-infra brief requires `creation_mode`, `ami_id`, `instance_size`, `timeout`. The backend stack endpoints need to accept all four; UI needs the schema. | Backend Architect |
| 10 | Is the 8-type registry the ceiling? | `PLUGIN_ORDER` contains 8 plugins. Container-runtime brief Sidecars (MITM, Neko, desktop) and Ephemeral-infra `sg-vault` push that to 12+. If the manifest is fixed at 8, plugins from external repos (the brief's eventual target) cannot land. | Backend Architect, Librarian |

---

## 6. Proposed next steps for the UI Architect role

Ordered. Do not execute; these are proposals.

1. Draft `team/roles/ui-architect/ROLE.md`. Mirror the structure of `team/roles/architect/ROLE.md` (Identity / Foundation / Primary Responsibilities / Core Workflows / Integration / Quality Gates / Tools / Escalation / For AI Agents). Explicitly call out the Architect-vs-UI-Architect split from Section 1 above so future agents pick the right role.
2. File a contract review for the plugin manifest (Boundary risks #1, #2, #10). Output: a typed manifest schema + a loader that reads `plugins/*/manifest.json` instead of the hard-coded `PLUGIN_ORDER` array. Coordinate with the backend Architect because the manifest needs a Type_Safe twin server-side.
3. Pin down the dashboard event vocabulary. Output: a `library/docs/specs/v{version}__ui-event-vocabulary.md` (or a UI-only fragment under `team/roles/ui-architect/specs/`) that lists every `sp-cli:*` event, its payload, and its emitter / listener. Coordinate with Librarian.
4. Publish a UI fragment of the reality doc. Either extend the existing reality doc at `team/roles/librarian/reality/` to include "what the dashboard actually renders today" or carve a sibling file `v{version}__ui-reality.md`. Coordinate with Librarian; respect rule "if not in the reality doc, it does not exist".
5. File a cleanup brief for the linux→podman rename residue (Boundary risk #7). Single PR by Dev, no schema impact.
6. File a contract review for `sp-cli-launch-modal` covering the three creation modes + AMI selector + size + timeout (ephemeral-infra Feature 2). Block before any of features 3-10 land, because the modal is the entry point for all of them.
7. File a contract review for the host-FastAPI control plane UI (container list / start / stop / logs / shell / metrics / sidecars). One component family, not five. Lands after the launch-modal contract.
8. File a vault-write UI contract (Boundary risk #4) before the Firefox MITM-script upload lands.

---

End.
