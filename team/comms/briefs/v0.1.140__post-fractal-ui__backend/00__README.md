# v0.1.140 — Post-Fractal-UI: Backend Contracts

**Status:** PROPOSED
**Owner:** Dev (backend) + Architect (review)
**Audience:** the backend team
**Paired with:** [`team/comms/briefs/v0.1.140__post-fractal-ui__frontend/`](../v0.1.140__post-fractal-ui__frontend/) — every contract here has a frontend consumer documented there.
**Source:** UI Architect orientation review at `team/humans/dinis_cruz/claude-code-web/05/01/15/ui-architect__pass-1__code-and-implementation.md` and `…__pass-2__scope-and-new-briefs.md`.

---

## Why this brief exists

The fractal-UI rebuild is ~70-75% landed at v0.1.140. The remaining gaps are not "more components" — they are **contracts the backend has not yet published** that the UI cannot fake any longer:

1. The dashboard discovers plugins by hard-coded arrays in five places (`PLUGIN_ORDER`, `LAUNCH_TYPES`, `settings-bus.DEFAULTS`, `<script>` tags, `Plugin__Registry`). Adding `firefox` and `podman` already required four parallel edits; the next plugin will have to do the same. The brief calls for a typed manifest endpoint.
2. The 05/01 ephemeral-infra brief introduces three creation modes (fresh / bake-AMI / from-AMI) plus AMI selection, instance size, and timeout. The current stack-creation request schema accepts `stack_name` only.
3. The 05/01 firefox brief adds a configuration column (credentials, MITM, security, profile, bake, health) that needs five new endpoint families. None exist today.
4. Several plugins want to persist secrets (firefox credentials, MITM scripts, browser profiles). There is no published vault-write contract for plugin-namespaced data.

These are backend-led pieces of work because the UI cannot move until the schemas exist.

---

## Items in this brief

| # | Topic | File | Frontend counterpart |
|---|-------|------|----------------------|
| 1 | Plugin manifest endpoint (typed) | `01__plugin-manifest-endpoint.md` | `frontend/01__plugin-manifest-loader.md` |
| 2 | Stack-creation payload — three modes | `02__stack-creation-payload-modes.md` | `frontend/02__launch-flow-three-modes.md` |
| 3 | Firefox configuration endpoints | `03__firefox-config-endpoints.md` | `frontend/03__firefox-configuration-column.md` |
| 4 | Per-plugin vault-write contract | `04__vault-write-contract.md` | `frontend/03__firefox-configuration-column.md` (first consumer) |

---

## Constraints

- All schemas extend `Type_Safe` from `osbot-utils`. No Pydantic. No raw primitives. No Literals — fixed-value sets are `Enum__*`. (`.claude/CLAUDE.md` rules.)
- One class per file. Empty `__init__.py`. (Rules 21, 22.)
- No new endpoint without a contract in the routes catalogue (`library/docs/specs/v0.20.55__routes-catalogue-v2.md`) and a Type_Safe schema in `library/docs/specs/v0.20.55__schema-catalogue-v2.md`.
- Routes have no logic — pure delegation to a service class.

---

## Lifecycle

1. Each topic file lands as a separate Architect review under `team/roles/architect/reviews/MM/DD/` before code is written.
2. Dev implements behind feature flags / capability profiles where appropriate.
3. The frontend brief tracks consumption; do not merge UI work until the matching backend contract is in place.
4. Each merged item is added to `team/roles/librarian/reality/v{version}/` and this brief is moved to `team/comms/briefs/archive/` with the closing-commit hash appended.
