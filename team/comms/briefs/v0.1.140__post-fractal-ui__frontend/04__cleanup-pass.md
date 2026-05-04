# 04 — Cleanup pass

## Goal

A single PR (or one PR per sub-section, frontend-Dev's call) that closes out the residual debt the fractal-UI rebuild and the linux→podman rename left behind. None of this is contract-blocked — it can land immediately and unblock the manifest loader (item 01) by reducing the surface that needs migration.

## 4.1 linux → podman rename residue

The rename merged via `3f1b75d` and `ba122af` removed `linux` from `PLUGIN_ORDER` but left nine UI references. Sweep them:

| File:line | What | Recommended action |
|-----------|------|--------------------|
| `sgraph_ai_service_playwright__api_site/shared/settings-bus.js:117` | `default_instance_types?.linux` reference | Rename key to `podman` in the defaults map; v1→v2 migration can drop `linux` (or keep as alias for one version). |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-settings-view/v0/v0.1/v0.1.0/sp-cli-settings-view.js:11` | Settings entry `{ name: 'linux', icon: '🐧', label: 'Bare Linux', stability: 'stable', boot: '~60s' }` | Replace with `podman` entry; or once item 01 lands, delete this hard-coded list entirely (settings view reads from manifest). |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-user-pane/v0/v0.1/v0.1.0/sp-cli-user-pane.css:76` | `.type-linux` colour token | Add `.type-podman`; keep `.type-linux` only if old user-page launches still render. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-stack-detail/v0/v0.1/v0.1.0/sp-cli-stack-detail.css:44` | `.type-linux` colour token | Falls out when `sp-cli-stack-detail` is removed (4.2). |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-stacks-pane/v0/v0.1/v0.1.0/sp-cli-stacks-pane.css:54` | `.type-linux` colour token | Add `.type-podman`; remove `.type-linux` if no legacy stacks render. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-stack-header/v0/v0.1/v0.1.0/sp-cli-stack-header.js:5` | `linux: '🐧'` icon map | Add `podman: '🦭'`; delete `linux` unless legacy. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-launch-form/v0/v0.1/v0.1.0/sp-cli-launch-form.html:4` | Placeholder `e.g. linux-nova-4217` | Update to a podman example. |
| `sgraph_ai_service_playwright__api_site/plugins/linux/v0/v0.1/v0.1.0/*` | Whole `plugins/linux/` folder | Delete. The card was orphaned from `PLUGIN_ORDER`; nothing references it. |
| `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-linux-detail/v0/v0.1/v0.1.0/*` | Whole detail folder | Delete unless legacy stacks still need to render. Confirm against backend whether any stack record can still have `type=linux`; if no, delete. |

Acceptance: a final `grep -RIn "linux" sgraph_ai_service_playwright__api_site/` returns only intentional results (e.g. user-agent strings, comments referencing the OS).

## 4.2 Remove deprecated components

The 04/29 brief specified deletion of these; today they remain on disk:

- `sp-cli-vnc-viewer/` — superseded by `_shared/sg-remote-browser/`.
- `sp-cli-launch-modal/` — superseded by `sp-cli-launch-panel/`.
- `sp-cli-stack-detail/` — superseded by per-plugin detail components.
- `sp-cli-vault-activity/` — superseded by `sp-cli-events-log/`.

Confirm no script tag in `admin/index.html` or `user/index.html` still imports these. Check the user page (`user.js:40`) which still uses `sp-cli-user-pane` and the legacy `sp-cli:user-launch` event — out of scope here, but verify no other accidental references remain.

Acceptance: the four directories above are deleted; `admin/index.html` no longer imports them; CI green.

## 4.3 Embed `<sg-remote-browser>` in the missing detail panels

Brief specified that elastic / prometheus / opensearch detail components host their respective UIs (Kibana, Prometheus UI, OpenSearch Dashboards) via `<sg-remote-browser>` in a split-column layout. Today these are single-column shells with no remote browser.

Files:

- `components/sp-cli/sp-cli-elastic-detail/v0/v0.1/v0.1.0/sp-cli-elastic-detail.{js,html,css}`
- `components/sp-cli/sp-cli-prometheus-detail/v0/v0.1/v0.1.0/sp-cli-prometheus-detail.{js,html,css}`
- `components/sp-cli/sp-cli-opensearch-detail/v0/v0.1/v0.1.0/sp-cli-opensearch-detail.{js,html,css}`

Required: import `_shared/sg-remote-browser`, render with `provider="iframe"`, point at the relevant URL on the stack record. Mirror the firefox detail's two-column layout (after item 03 lands the layout pattern can be lifted into `_shared/sp-cli-detail-split-layout` if Dev decides it is worth the abstraction — three users justify it).

Acceptance: the three detail components render the live UI when the stack is `RUNNING`.

## 4.4 Card-label vs provider consistency

`plugins/firefox/v0/v0.1/v0.1.0/sp-cli-firefox-card.js:3` declares `display_name: 'Firefox (noVNC)'`; the detail uses `provider: 'iframe'`. Pick one — recommendation: `display_name: 'Firefox'`, `provider` as a manifest capability. This may be done as part of brief item 03; cross-link.

## 4.5 Plugin-folder structure decision

The 04/29 brief said `plugins/{name}/` should hold both `card.{js,html,css}` AND `detail.{js,html,css}`. Reality kept cards under `plugins/{name}/...` and details under `components/sp-cli/sp-cli-{name}-detail/...`. Pick one and document the choice.

Recommendation: ratify the current split (`plugins/{name}/` for the launcher card; `components/sp-cli/sp-cli-{name}-detail/` for the detail panel). It is functionally equivalent and avoids deep `plugins/{name}/{detail,card}/...` nesting. Update the 04/29 brief or write a UI Architect ROLE.md decision log entry to record the divergence as accepted.

Acceptance: a one-page decision note filed under (TBD: `team/roles/ui-architect/decisions/v{version}__plugin-folder-structure.md`) once the UI Architect ROLE folder is created.

## Acceptance criteria (overall)

- Each of 4.1, 4.2, 4.3 lands in its own commit.
- 4.4 and 4.5 are decision/documentation only; no code beyond the card label tweak.
- A reality-doc UI fragment is updated reflecting the deletions.
- CI green.

## Open questions

1. **Backwards compat for `type=linux` stack records.** If users have running linux stacks at deletion time, the UI must still render them somehow. Confirm with backend: are there any live `type=linux` stacks, and is there a migration path?
2. **Decision-log location.** The UI Architect ROLE.md does not exist yet (proposed in pass-2 of the orientation review). For now, write decisions under `team/humans/dinis_cruz/claude-code-web/MM/DD/HH/` and migrate once the role folder exists.

## Out of scope

- Manifest-driven discovery (item 01).
- Anything that changes plugin behaviour, only naming and dead-code removal.

## Paired-with

- This brief is **not blocked** on any backend item. Recommend landing it first to reduce the surface for items 01-03.
