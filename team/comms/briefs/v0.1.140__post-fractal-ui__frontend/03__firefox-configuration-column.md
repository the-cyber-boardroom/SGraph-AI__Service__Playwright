# 03 — Firefox configuration column

## Goal

Build the configuration column the 05/01 firefox brief calls for inside `sp-cli-firefox-detail`. Today the detail is an iframe shell only; the brief requires five sub-panels (Configuration / MITM Proxy / Security / Firefox Settings / Instance) that together turn the firefox plugin into a real workbench.

## Today

- Detail component: `sgraph_ai_service_playwright__api_site/components/sp-cli/sp-cli-firefox-detail/v0/v0.1/v0.1.0/sp-cli-firefox-detail.{js,html,css}` (commit `092f069`).
- Wires `<sg-remote-browser provider="iframe">` (`sp-cli-firefox-detail.js:54`). Single column.
- Card: `sgraph_ai_service_playwright__api_site/plugins/firefox/v0/v0.1/v0.1.0/sp-cli-firefox-card.js`. `display_name: 'Firefox (noVNC)'` disagrees with the detail's `provider: 'iframe'` — fix as part of this brief OR in the cleanup brief. Recommended: fix here, since this brief is the firefox-detail owner.
- Grep for `MITM`, `credentials`, `username`, `password`, `intercept`, `bake`, `health` across `sp-cli-firefox-detail/` returns nothing today. Configuration column = PROPOSED — does not exist yet.

## Required output

Restructure `sp-cli-firefox-detail` to a two-column layout:

```
┌─────────────────────────────────────┬──────────────────────────────┐
│  <sg-remote-browser>                │  Configuration               │
│  (iframe to https://{ip}/)          │   • Username / Password      │
│                                     │   • [Update Credentials]     │
│                                     │                              │
│                                     │  MITM Proxy                  │
│                                     │   • Status (chip)            │
│                                     │   • Intercept script [▼]     │
│                                     │   • [Upload Script]          │
│                                     │   • [Open Proxy UI ↗]        │
│                                     │                              │
│                                     │  Security                    │
│                                     │   • [✓] Self-signed certs    │
│                                     │   • [✓] SSL intercept        │
│                                     │                              │
│                                     │  Firefox Settings            │
│                                     │   • Start page [          ]  │
│                                     │   • [Load Profile]           │
│                                     │                              │
│                                     │  Instance                    │
│                                     │   • Health: ● green          │
│                                     │   • [Bake AMI]   [Stop]      │
└─────────────────────────────────────┴──────────────────────────────┘
```

### Components

- `sp-cli-firefox-detail` becomes a layout host. The five sub-panels are children:
  - `sp-cli-firefox-credentials/` (new)
  - `sp-cli-firefox-mitm/` (new) — uses `sp-cli-vault-blob-picker` (new shared widget — see below) + status chip
  - `sp-cli-firefox-security/` (new)
  - `sp-cli-firefox-profile/` (new)
  - `sp-cli-firefox-instance/` (new) — wraps `sp-cli-stop-button` + a new health-badge widget + a "Bake AMI" trigger that emits `sp-cli:plugin:firefox.bake-requested`
- New shared widget under `_shared/`:
  - `sp-cli-vault-blob-picker/` — generic "list / select / upload" against the vault-write contract (`backend/04__vault-write-contract.md`). First consumer is firefox MITM scripts; second consumer is firefox profiles; third will be cross-plugin (podman sidecars).
  - `sp-cli-health-badge/` — green / amber / red dot + drill-down popover. Consumes the per-plugin `GET /firefox/{stack_id}/health` response (or the equivalent for other plugins later).

### Events

- New: `sp-cli:plugin:firefox.bake-requested` ({ stack_id }).
- Reused: `sp-cli:plugin:firefox.stop-requested`, `sp-cli:stack.deleted`.
- Settings panels emit `sp-cli:plugin:firefox.settings-changed` ({ stack_id, key, value }) for the audit log.
- Vault writes emit `sp-cli:vault.written` ({ plugin_id, handle }) — listened by `sp-cli-events-log` (see backend brief 04, open question 2).

## Acceptance criteria

- All five sub-panels render and their state matches the firefox endpoints (`backend/03__firefox-config-endpoints.md`).
- Health badge polls every 10 s; shows the red drill-down detail string from the health response.
- Card label updated to align with the detail provider — recommend `display_name: 'Firefox'` and a separate `provider` capability flag from the manifest.
- Vault-blob picker is generic enough that podman / future plugins can reuse it without copy-paste.
- "Bake AMI" launches the bake flow (which is the same backend AMI-bake path used by the launch panel's BAKE_AMI mode — single underlying mechanism).
- All new components live under `{name}/v0/v0.1/v0.1.0/{name}.{js,html,css}`. Three-file pattern. No build step.
- Snapshot tests for each sub-panel (loading, ready, error states).
- Reality doc UI fragment updated to enumerate the eight firefox sub-components and the new shared widgets.

## Open questions

1. **Order of sub-panels.** Brief lines 44-66 list them top-to-bottom; confirm the order in review.
2. **Read-only mode.** When the vault is not attached (post-`e34c2e6`), should the configuration column show a "no vault — read-only" banner and disable mutation, or hide the column entirely? Recommendation: banner + disabled state, mirroring the existing settings-view pattern.
3. **Profile size.** Browser profiles can be hundreds of MB. The vault-write contract caps at 10 MB by default; we either raise the cap for `firefox/profile` or fall back to a separate large-blob path. Backend call.
4. **MITM script preview.** Before activating a script, do we show its content? Recommendation: read-only preview pane below the picker, expandable.
5. **Card label vs provider.** Two ways to fix:
   - (a) Card label "Firefox" + manifest capability `iframe-embed`.
   - (b) Card label "Firefox (iframe)".
   Recommendation: (a) — the card name should be the plugin, not the rendering strategy.

## Out of scope

- Cross-plugin "templates" (apply the same MITM script to multiple stacks). v2.
- Sidecar UI (Neko fallback). Container-runtime brief.
- Activity log of firefox-specific events. Falls out from the existing events-log path.

## Paired-with

- Backend contracts: `../v0.1.140__post-fractal-ui__backend/03__firefox-config-endpoints.md` and `04__vault-write-contract.md`.
- Source: `team/humans/dinis_cruz/briefs/05/01/v0.22.19__dev-brief__firefox-browser-plugin.md`.
- Blocked by: both backend items must land first.
