# FV2.9 — Migrate `sp-cli:plugin:*` → `sp-cli:spec:*`; publish event vocabulary spec

## Goal

The frontend audit found F4 was half-done: entity events (`stack.*` → `node.*`) migrated with deprecated aliases, but **per-type namespace** (`sp-cli:plugin:firefox.launch-requested` → `sp-cli:spec:firefox.launch-requested`) was NOT migrated. Emitters in spec cards + listeners in `admin.js` still use `plugin:`. Also: no event vocabulary spec exists at `library/docs/specs/`.

## Tasks

### Part 1 — Per-type namespace migration

1. **For each per-spec card** at `plugins/<name>/v0/v0.1/v0.1.0/sp-cli-<name>-card.js` — change emitter:
   ```
   sp-cli:plugin:firefox.launch-requested → sp-cli:spec:firefox.launch-requested
   ```
   Dispatch BOTH names for one release (deprecated alias).
2. **In `admin.js`** — listen for both names; mark the legacy name DEPRECATED in the comment.
3. **In `sp-cli-events-log.js`** — update the `FAMILIES` map to register both forms; mark the old form `DEPRECATED`.
4. **In `sp-cli:settings.toggled`** family — `sp-cli:plugin.toggled` becomes `sp-cli:spec.toggled` (same back-compat dance).

### Part 2 — Event vocabulary spec

Publish a spec at `library/docs/specs/v0.2.0__ui-event-vocabulary.md` that lists every dashboard event with:

| Event name | Emitter (file:line) | Listener (file:line) | Payload schema | Status |

Status one of: `ACTIVE`, `RESERVED`, `DEPRECATED`. Include hyphen-form back-compat aliases.

The `sp-cli-events-log.js` `FAMILIES` map becomes a generated artefact from this spec (or stays in code as the implementation; the spec is the doc).

## Tasks summary

1. Migrate per-type emitters in 12 spec cards.
2. Migrate per-type listener in `admin.js`.
3. Update `FAMILIES` map.
4. Write the event vocabulary spec.
5. Update reality doc / PR description.

## Acceptance criteria

- All per-spec card emitters use `sp-cli:spec:<name>.*` (with deprecated alias).
- `admin.js` listens for both forms.
- `FAMILIES` map enumerates every event with status.
- `library/docs/specs/v0.2.0__ui-event-vocabulary.md` exists.
- Snapshot tests updated.

## Open questions

- **Deprecated alias removal deadline.** Recommend v0.3.0 — gives one release for any external listener to migrate.

## Blocks / Blocked by

- **Blocks:** FV2.12 (cosmetic rename) — finish event vocabulary first.
- **Blocked by:** none. Independent.

## Notes

The spec at `library/docs/specs/` is the **single source of truth** for event names. Anyone adding a new dashboard event must update it.
