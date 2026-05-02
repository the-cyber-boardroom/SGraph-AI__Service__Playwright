# 05 — Governance decisions

## Goal

Get explicit human / Architect blessing on three decisions the dashboard has already taken without going through brief review, and pin down the event vocabulary as a published spec before the next plugin lands.

These items are decision-only (no code, except the card-label tweak in 5.1 which can ride with brief 04). They block nothing but should be settled before the next round of plugin work begins.

## 5.1 Out-of-brief plugin: `firefox`

The 04/29 fractal-UI brief enumerated seven plugins: linux / docker / elastic / vnc / prometheus / opensearch / neko. Reality at v0.1.140 has eight (linux retired in favour of podman; firefox added). Firefox shipped on the back of `c5566d2` and `092f069` plus the dedicated 05/01 firefox brief, but it bypassed the fractal-UI brief.

Decision needed:

- (a) Treat firefox as a ratified addition — update the 04/29 brief or supersede it with a reality-doc shard.
- (b) Roll back firefox UI — unlikely given the 05/01 brief explicitly invests in it.

Recommendation: (a). Update the reality doc UI fragment to list eight plugins. Append a one-line decision note to `team/roles/ui-architect/decisions/` (folder TBD).

## 5.2 Out-of-brief navigation: `api` view

The 04/29 brief specified four nav items: Compute / Storage / Settings / Diagnostics. `c5566d2` added a fifth — `api` — and a corresponding `<sp-cli-api-view>`. References:

- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-left-nav/v0/v0.1/v0.1.0/sp-cli-left-nav.html:23-26`
- `sgraph_ai_service_playwright__api_site/admin/admin.js:33,308,323`

Decision needed:

- (a) Ratify and document the five-nav layout. Update the 04/29 brief.
- (b) Roll back, route the API docs through a different surface (top-bar link, top-right kebab menu, etc.).

Recommendation: (a) — having the API docs one click away from the dashboard is genuinely useful. But the visual budget for the nav is finite; once a sixth item is proposed, this decision sets the precedent.

## 5.3 Reserved-but-unimplemented events

The 04/29 event-vocabulary brief reserved several events that have no emitter or listener in code:

- `sp-cli:plugin:elastic.import-requested`
- `sp-cli:plugin:elastic.export-requested`
- `sp-cli:plugin:elastic.screenshot-requested`
- `sp-cli:plugin:playwright.*`
- `sp-cli:plugin:vnc.viewer-mode-toggled`
- `sp-cli:detail-closed`

Decision needed: do these stay reserved (documented but unused), or do they get exercised before the next plugin lands?

Recommendation: keep reserved. They mark intent; emitting them only when wired keeps the audit log honest. Do publish them in the event vocabulary spec (5.4) so future implementers know the slots exist.

## 5.4 Publish the event vocabulary as a spec

The dashboard's event vocabulary lives implicitly in:

- `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-events-log/v0/v0.1/v0.1.0/sp-cli-events-log.js:14` — the `FAMILIES` map (closest thing to a canonical list).
- `sgraph_ai_service_playwright__api_site/admin/admin.js:75-162` — the controller's listener wiring.
- The 04/29 brief `03__event-vocabulary.md`, which is aspirational rather than code-verified.

Required output: a single spec under (TBD path — recommend `library/docs/specs/v{version}__ui-event-vocabulary.md`) listing every dashboard event with:

| Event name | Emitter (file:line) | Listener (file:line) | Payload | Status |

Status is one of: ACTIVE / RESERVED / DEPRECATED. The spec is the single source of truth — `sp-cli-events-log.FAMILIES` becomes a generated artefact.

Acceptance:

- The spec lists every event found by `grep -RIn "CustomEvent\\|dispatchEvent" sgraph_ai_service_playwright__api_site/`.
- Reserved events from 5.3 appear with status RESERVED.
- Hyphen-form back-compat aliases (`stack-selected` etc., from `admin.js:75-80`) listed and tagged DEPRECATED.
- Every plugin-specific event uses the `sp-cli:plugin:{type_id}.{verb}` shape.

## 5.5 UI-panel re-show UX

Hiding a right-info panel via Settings removes it; re-enabling it requires a manual layout reset (`sp-cli-settings-view.js:120-123`). The brief implied live re-show. Decide:

- (a) Implement live re-show.
- (b) Update the brief to ratify the "reset layout" UX.

Recommendation: (a) for consistency with the live-hide already implemented. Tracking under brief item 04/29 PR-3 polish; assign to UI Dev.

## 5.6 Vault-optional flow

Commit `e34c2e6` removed the vault gate. The 04/29 brief assumed a vault-required boot path. Decide whether to ratify the new "vault optional" UX as the standard.

Recommendation: ratify. The fact that the dashboard already boots without a vault is well-isolated and reduces friction for read-only diagnosis. Implications carried into briefs 01 and 03 (`Schema__Vault__Write__Receipt` returns 409 with `NO_VAULT_ATTACHED` error code; UI shows a degraded-mode banner).

## Acceptance criteria

- Each decision lands as a one-line entry in the appropriate decision log (initially `team/humans/dinis_cruz/claude-code-web/MM/DD/HH/decisions__post-fractal-ui.md`; migrate to `team/roles/ui-architect/decisions/` once the role folder is created).
- The event vocabulary spec lands at the agreed path.
- Reality doc UI fragment reflects the ratified additions (firefox plugin, api nav, vault-optional).

## Open questions

- Where does the UI Architect role's decision log live? Proposed: `team/roles/ui-architect/decisions/MM/DD/`. Awaits the ROLE.md draft.

## Paired-with

- Source: orientation review pass-1 §3 ("Recently merged UI changes"), pass-2 §5 ("Boundary risks") and §6 ("Proposed next steps").
- Not blocked on backend items.
