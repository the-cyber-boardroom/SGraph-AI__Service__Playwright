# T2.4 — settings-bus dual-dispatch (`sp-cli:plugin.toggled` → `sp-cli:spec.toggled`)

⚠ **Tier 2 — contract violation.** Standalone PR.

## What's wrong

FV2.9 brief Task 1.4 required migrating `sp-cli:plugin.toggled` → `sp-cli:spec.toggled` in `shared/settings-bus.js` with **dual-dispatch** (both names emitted for one release).

What shipped:

- ✅ Per-spec card emitters migrated to `sp-cli:spec:{name}.launch-requested`.
- ❌ `shared/settings-bus.js` not touched. Still dispatches `sp-cli:plugin.toggled` only.
- The published event-vocabulary spec (`library/docs/specs/v0.2.0__ui-event-vocabulary.md`) lists `sp-cli:spec.toggled` as **RESERVED** — wishful, not actual.

## Why it matters

Listeners that subscribe to `sp-cli:spec.toggled` (the new vocabulary) will silently never fire. The published spec is misleading.

## Tasks

1. **Find the dispatch site** — `shared/settings-bus.js` — locate `dispatchEvent(new CustomEvent('sp-cli:plugin.toggled', ...))`.
2. **Add dual-dispatch** — emit BOTH `sp-cli:plugin.toggled` (deprecated alias) AND `sp-cli:spec.toggled` (canonical).
3. **Update the listener** in `admin/admin.js` — listen for both forms; prefer the new one.
4. **Update `sg-compute-events-log` `FAMILIES` map** — list both events; status `ACTIVE` for `sp-cli:spec.toggled`, `DEPRECATED` for `sp-cli:plugin.toggled` with a removal date (recommend v0.3.0).
5. **Update `library/docs/specs/v0.2.0__ui-event-vocabulary.md`** — change `sp-cli:spec.toggled` from RESERVED to ACTIVE.
6. **Test** — toggle a spec in Settings; observe the events log shows both events firing.

## Acceptance criteria

- `shared/settings-bus.js` dispatches both event names.
- `admin/admin.js` listens for both.
- `FAMILIES` map updated (ACTIVE / DEPRECATED).
- Spec doc updated to reflect reality.
- Events log shows both events when a spec is toggled.

## "Stop and surface" check

If you find listeners elsewhere that depend on the old name only and migrating them is out-of-scope for this PR: **STOP** and document — leave the deprecated alias in for one release; file a follow-up brief for the listener migration.

## Live smoke test (acceptance gate)

Open the dashboard. Open the events log panel. Toggle a spec in Settings. Both `sp-cli:plugin.toggled` and `sp-cli:spec.toggled` appear in the events log. Screenshot; attach.

## Source

Executive review Tier-2; frontend-late review §"Missed requirement #2 (FV2.9)".
