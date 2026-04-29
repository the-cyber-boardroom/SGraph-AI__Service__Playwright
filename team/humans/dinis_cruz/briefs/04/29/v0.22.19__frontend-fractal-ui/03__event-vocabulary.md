# 03 — Event Vocabulary

**Status:** PROPOSED
**Read after:** `02__component-architecture.md`
**Audience:** anyone wiring an emit or listen

---

## What this doc gives you

The complete inventory of DOM events the frontend uses. Existing events (preserved as-is). New events introduced by this brief. Naming convention for adding new events. Stable-vs-experimental flag per event.

## The convention

`{family}:{action}` colon-separated for top-level events.

For plugin-specific events: `sp-cli:plugin:{plugin}.{noun}.{verb}` — three colons, then dotted within the plugin scope. This prevents collision when many plugins emit similar events.

Payload conventions:
- Always pass an object as `detail`, never a primitive
- `bubbles: true, composed: true` on every CustomEvent
- Type-Safe-style field names (snake_case in JSON, but our DOM events have always used camelCase per JS conventions — keep camelCase)

## The full inventory

### Vault events (existing — preserved)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `vault:connected` | `<sg-vault-connect>` (Tools) | `vault-bus.js`, `<sp-cli-vault-picker>`, page controller | `{ vault, session, vaultId, apiBaseUrl, keys }` | stable |
| `vault:disconnected` | `<sg-vault-connect>`, `<sp-cli-vault-picker>` | same | `{}` | stable |

### Vault-bus trace events (existing — preserved)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sp-cli:vault-bus:read-started` | `vault-bus.js`'s `vaultReadJson` | `<sp-cli-events-log>` | `{ traceId, path, vaultId }` | stable |
| `sp-cli:vault-bus:read-derived-id` | same | same | `{ traceId, path, fileId }` | stable |
| `sp-cli:vault-bus:read-completed` | same | same | `{ traceId, path, fileId, bytes, durationMs }` | stable |
| `sp-cli:vault-bus:read-not-found` | same | same | `{ traceId, path, durationMs }` | stable |
| `sp-cli:vault-bus:read-error` | same | same | `{ traceId, path, error, durationMs }` | stable |
| `sp-cli:vault-bus:write-started` | `vault-bus.js`'s `vaultWriteJson` | same | `{ traceId, path, bytes, vaultId }` | stable |
| `sp-cli:vault-bus:write-completed` | same | same | `{ traceId, path, bytes, commitId, blobId, durationMs }` | stable |
| `sp-cli:vault-bus:write-error` | same | same | `{ traceId, path, error, durationMs, reason? }` | stable |

### Stack lifecycle events (existing + extended)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sp-cli:stack.selected` | `<sp-cli-stacks-pane>`, `<sp-cli-user-pane>` | page controller (opens detail tab) | `{ stack }` | stable |
| `sp-cli:stack.stop-requested` | `<sp-cli-{type}-detail>`, stack-card overflow menu | page controller (calls DELETE) | `{ stack }` | stable |
| `sp-cli:stack.deleted` | page controller after successful DELETE | `<sp-cli-events-log>`, all detail tabs (close-if-match) | `{ stack }` | stable |
| `sp-cli:stack.launched` | page controller after successful POST | `<sp-cli-events-log>`, `<sp-cli-stacks-pane>` (refresh) | `{ entry, stack }` | stable |
| `sp-cli:stacks.refresh` | refresh button, periodic poll | page controller | `{}` | stable |

Note: `sp-cli:stack.selected` was previously `sp-cli:stack-selected` (hyphenated). **This brief renames** to `.selected` (dotted noun.verb) to match the broader convention. Both names work for one release; the old name is logged as deprecated.

### Launch flow events (renamed)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sp-cli:plugin:{name}.launch-requested` | `<sp-cli-{name}-card>` | page controller (opens launch tab) | `{ entry }` | stable |
| `sp-cli:launch.submitted` | `<sp-cli-launch-panel>` form submit | page controller (calls POST) | `{ entry, formData }` | stable |
| `sp-cli:launch.success` | page controller after successful POST | `<sp-cli-events-log>`, `<sp-cli-launch-panel>` (close-tab) | `{ entry, response }` | stable |
| `sp-cli:launch.error` | page controller after failed POST | `<sp-cli-events-log>`, `<sp-cli-launch-panel>` (show error) | `{ entry, error }` | stable |

Deprecated (from prior version): `sp-cli:catalog-launch`, `sp-cli:user-launch`. Both still fire for one release for back-compat with `<sp-cli-stacks-pane>` and `<sp-cli-user-pane>`. Documented in the deprecations section below.

### Navigation events (new)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sp-cli:nav.selected` | `<sp-cli-left-nav>` | page controller (replaces main view) | `{ view: 'compute' \| 'storage' \| 'settings' \| 'diagnostics' }` | stable |

### Settings / feature-toggle events (new)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sp-cli:plugin.toggled` | `<sp-cli-settings-view>` | `<sp-cli-launcher-pane>`, page controller (close detail tabs for disabled plugin) | `{ name, enabled }` | stable |
| `sp-cli:ui-panel.toggled` | `<sp-cli-settings-view>` | page controller (hide/show right-panel sections) | `{ panel, visible }` | experimental |
| `sp-cli:settings.saved` | `settings-bus.js` after persist | `<sp-cli-events-log>` | `{ keys: [string] }` | stable |
| `sp-cli:settings.loaded` | `settings-bus.js` after vault read | `<sp-cli-launcher-pane>` (re-render with current toggles) | `{ settings }` | stable |

### Region events (existing — preserved)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sp-cli:region-changed` | `<sp-cli-region-picker>` | page controller (re-fetches stacks for new region) | `{ region }` | stable |

### Auth events (existing — preserved)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sg-auth-required` | `api-client.js` on 401 | `<sg-auth-panel>` (opens drawer) | `{}` | stable |
| `sg-show-auth` | page controller | same | `{}` | stable |
| `sg-auth-saved` | `<sg-auth-panel>` | page controller (re-fetch data) | `{}` | stable |

### Top-bar / vault-picker events (existing — preserved)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sp-cli:brand-clicked` | `<sp-cli-top-bar>` | page controller (navigate home) | `{}` | stable |
| `sp-cli:vault-picker-opened` | `<sp-cli-vault-picker>` | (none currently — telemetry hook) | `{}` | experimental |
| `sp-cli:vault-connected` | `<sp-cli-vault-picker>` (proxy of `vault:connected`) | (deprecated — listen for `vault:connected` directly) | same as `vault:connected` | deprecated |
| `sp-cli:vault-disconnected` | same | (deprecated — listen for `vault:disconnected`) | same | deprecated |

### Plugin-specific events (new — examples)

These fire from per-plugin detail views when plugin-specific actions are taken. Backend handlers come later; for this brief they fire and the events log shows them.

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sp-cli:plugin:elastic.import-requested` | `<sp-cli-elastic-detail>` | (no listener yet) | `{ stack }` | experimental |
| `sp-cli:plugin:elastic.export-requested` | same | (no listener yet) | `{ stack }` | experimental |
| `sp-cli:plugin:elastic.screenshot-requested` | same | (no listener yet) | `{ stack }` | experimental |
| `sp-cli:plugin:playwright.screenshot-requested` | `<sp-cli-playwright-detail>` | (no listener yet) | `{ stack }` | experimental |
| `sp-cli:plugin:playwright.sequence-run-requested` | same | (no listener yet) | `{ stack, sequence_id }` | experimental |
| `sp-cli:plugin:vnc.viewer-mode-toggled` | `<sp-cli-vnc-detail>` | inner `<sg-remote-browser>` | `{ mode: 'viewer' \| 'mitmweb' }` | experimental |

These are documented here but their handlers are placeholders. The point is the **vocabulary is reserved** so when backend support lands, no naming churn.

### Activity log entries (existing — application-level audit)

Distinct from `<sp-cli-events-log>` (which shows DOM events). The application activity log is the audit trail of what stacks were provisioned, by whom, when. Stored in `sp-cli/activity-log.json`.

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sp-cli:activity-entry` | page controller | `<sp-cli-activity-pane>` (which writes to vault) | `{ message }` | stable |

This is the existing event from the prior brief; this brief preserves it. The activity *pane* (`<sp-cli-activity-pane>`) and the events *log* (`<sp-cli-events-log>`) are different components — the pane is application-level audit; the log is DOM-event tracing.

### sg-remote-browser events (new)

| Event | Fired by | Listened by | Payload | Stability |
|---|---|---|---|---|
| `sg-remote-browser:state.changed` | `<sg-remote-browser>` | (no required listener; useful for debug) | `{ state, provider }` | experimental |
| `sg-remote-browser:fallback-applied` | `<sg-remote-browser>` | (no required listener) | `{ from, to, url }` | experimental |

## Naming guidance for new events

If adding an event:

1. **Top-level, app-wide?** → `sp-cli:{noun}.{verb}` (e.g. `sp-cli:nav.selected`)
2. **Plugin-specific?** → `sp-cli:plugin:{name}.{noun}.{verb}` (e.g. `sp-cli:plugin:elastic.import-requested`)
3. **Lifecycle of a thing?** → `{thing}:{verb}` (e.g. `vault:connected`)
4. **Tracing / fine-grained progress?** → `{family}:{component}:{step}` (e.g. `sp-cli:vault-bus:read-started`) — only for things that benefit from a trace pane

Past-tense verbs for facts (`.created`, `.deleted`, `.completed`). Present-imperative-ish for requests (`.launch-requested`, `.stop-requested`, `.import-requested`). The `-requested` suffix is the marker that this is "asking for something to happen" rather than "announcing it did."

## Listener responsibility

If you're listening for an event:

1. Check `e.detail` exists; bail gracefully if not.
2. Don't throw — uncaught errors propagate up; if you can't handle it, log and move on.
3. Don't re-emit the same event from your handler (infinite loop risk).
4. If you're handling cross-cutting concerns (logging, metrics), use `addEventListener` on `document`, not on a specific element.
5. Clean up listeners in `disconnectedCallback` (the `SgComponent` base class handles this for tracked listeners).

## Deprecations

Events being phased out over the next release:

| Old name | New name | Removal target |
|---|---|---|
| `sp-cli:stack-selected` | `sp-cli:stack.selected` | v0.23.x |
| `sp-cli:catalog-launch` | `sp-cli:plugin:{name}.launch-requested` | v0.23.x |
| `sp-cli:user-launch` | `sp-cli:plugin:{name}.launch-requested` | v0.23.x |
| `sp-cli:launch-success` | `sp-cli:launch.success` | v0.23.x |
| `sp-cli:launch-error` | `sp-cli:launch.error` | v0.23.x |
| `sp-cli:stacks-refresh` | `sp-cli:stacks.refresh` | v0.23.x |
| `sp-cli:vault-connected` (proxy) | listen to `vault:connected` directly | v0.23.x |
| `sp-cli:vault-disconnected` (proxy) | listen to `vault:disconnected` directly | v0.23.x |

For this brief, **both names fire**. Components emit the new name and also (where existing listeners depend on it) the old name. Listeners listen for the new name. New code uses only the new name.

## Frontend ↔ backend event correspondence

The backend event bus (per backend brief) uses similar naming. Frontend events are DOM-events (different runtime) but the conceptual mapping is:

| Backend event | Frontend event | Relation |
|---|---|---|
| `linux:stack.created` | `sp-cli:stack.launched` | Backend fires when create_stack succeeds; frontend fires after the POST returns success. Same fact, different observer. |
| `vnc:stack.deleted` | `sp-cli:stack.deleted` | Same shape. |
| `core:plugin.loaded` | `sp-cli:plugin.toggled { enabled: true }` | Backend fires at startup; frontend fires when operator toggles in settings. Different triggers, same direction (a plugin became active). |

There is no wire-level bridging — frontend events stay in the browser; backend events stay in the FastAPI process. The naming alignment means an operator looking at "stack lifecycle" from either side sees the same vocabulary. **The future vault-bus brief is what unifies them**, not this brief.
