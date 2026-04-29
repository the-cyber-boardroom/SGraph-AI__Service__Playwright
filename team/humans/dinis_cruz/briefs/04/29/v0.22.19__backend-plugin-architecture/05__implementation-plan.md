# 05 — Implementation Plan

**Status:** PROPOSED
**Read after:** all of `00`–`04`
**Audience:** Sonnet planning the PR sequence

---

## What this doc gives you

The PR sequence in dependency order, files touched per PR, acceptance per PR. ~5 PRs, 4–6 dev-days for one developer.

## Pre-flight

Working from a clean branch off `dev`:

```bash
git checkout dev && git pull
git checkout -b claude/v0_22_19_backend_plugin_architecture
```

Read these existing files before starting — they're the patterns you're rebasing onto:

| File | Read for |
|---|---|
| `sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py` | The current mounting pattern you're refactoring |
| `sgraph_ai_service_playwright__cli/catalog/service/Stack__Catalog__Service.py` | Hard-coded list_types you're moving to registry |
| `sgraph_ai_service_playwright__cli/catalog/schemas/Schema__Stack__Type__Catalog__Entry.py` | Existing catalog entry — preserved |
| `sgraph_ai_service_playwright__cli/vnc/service/Vnc__Service.py` | Reference for service shape; you'll add `event_bus.emit` here |
| `sgraph_ai_service_playwright__cli/linux/service/Linux__Service.py` | Same |
| Reality doc `team/roles/librarian/reality/v0.1.31/14__sp-cli-ui-sg-layout-vnc-wiring.md` | What's currently shipped on the SP-CLI surface |

---

## PR sequence

```
PR-1   Core scaffolding (event bus + plugin base + registry)         ◀── start here
  │
PR-2   Migrate 6 existing plugins to manifests + registry              ◀── needs PR-1
  │
PR-3   Refactor Fast_API__SP__CLI + Stack__Catalog__Service            ◀── needs PR-2
  │
PR-4   Wire emit calls into existing services + audit listener tests   ◀── needs PR-3
  │
PR-5   Neko stub plugin + experiment scaffolding                       ◀── needs PR-2 (parallel possible)
```

PR-5 can run in parallel with PR-3+ once PR-2 lands.

---

## PR-1 — Core scaffolding

**Goal:** the new `core/` sub-package exists with `Event__Bus`, `Plugin__Manifest__Base`, and `Plugin__Registry`. No existing functionality affected.

### Files created

- `sgraph_ai_service_playwright__cli/core/__init__.py`
- `sgraph_ai_service_playwright__cli/core/event_bus/__init__.py`
- `sgraph_ai_service_playwright__cli/core/event_bus/Event__Bus.py` — full impl per doc 02
- `sgraph_ai_service_playwright__cli/core/event_bus/schemas/__init__.py`
- `sgraph_ai_service_playwright__cli/core/event_bus/schemas/Schema__Stack__Event.py`
- `sgraph_ai_service_playwright__cli/core/event_bus/schemas/Schema__Plugin__Event.py` (for `core:plugin.*`)
- `sgraph_ai_service_playwright__cli/core/plugin/__init__.py`
- `sgraph_ai_service_playwright__cli/core/plugin/Plugin__Manifest__Base.py` — full impl per doc 01
- `sgraph_ai_service_playwright__cli/core/plugin/Plugin__Registry.py` — full impl per doc 01
- `tests/unit/sgraph_ai_service_playwright__cli/core/event_bus/test_Event__Bus.py`
- `tests/unit/sgraph_ai_service_playwright__cli/core/plugin/test_Plugin__Manifest__Base.py`
- `tests/unit/sgraph_ai_service_playwright__cli/core/plugin/test_Plugin__Registry.py`

### Tests

For `Event__Bus`:
- `test__emit_with_no_listener__silently_drops__returns_zero`
- `test__emit_with_listener__delivers__returns_one`
- `test__multiple_listeners__all_invoked`
- `test__listener_exception__caught_and_logged__other_listeners_still_invoked`
- `test__off__removes_listener`
- `test__reset__clears_all_listeners`

For `Plugin__Registry`:
- `test__discover__with_no_plugin_folders__loads_nothing`
- `test__discover__with_one_disabled_in_manifest__skipped`
- `test__discover__with_env_override_disable__skipped`
- `test__discover__with_broken_import__failed_event_emitted__continues`
- `test__discover__emits_loaded_event_per_plugin`

For `Plugin__Manifest__Base`:
- `test__base_class__abstract_methods_raise`
- `test__subclass__concrete_methods_invoked`

### Acceptance

- `pytest tests/unit/sgraph_ai_service_playwright__cli/core/` passes.
- `grep -r "from sgraph_ai_service_playwright__cli.core" sgraph_ai_service_playwright__cli/` returns only test imports — nothing else uses it yet.
- The existing `Fast_API__SP__CLI` is unchanged. Existing tests still pass.

### Effort

**0.5–1 day.** Mostly mechanical — Type_Safe schemas, the bus is ~50 lines, the registry is ~80 lines. Tests are the bulk of the work.

---

## PR-2 — Migrate existing plugins to manifests

**Goal:** each of the 6 existing types has a manifest. The registry can discover and load them. **Nothing else changes** — `Fast_API__SP__CLI` still hand-mounts everything.

### Files created (per type)

For each of `linux`, `docker`, `elastic`, `vnc`, `prometheus`, `opensearch`:
- `sgraph_ai_service_playwright__cli/{type}/plugin/__init__.py`
- `sgraph_ai_service_playwright__cli/{type}/plugin/Plugin__Manifest__{Type}.py`

### Files touched

- `sgraph_ai_service_playwright__cli/core/plugin/Plugin__Registry.py` — `PLUGIN_FOLDERS` populated with the 6 names
- (No changes to `Fast_API__SP__CLI` yet — that's PR-3)

### Per-manifest content

Each manifest declares:
- `name`, `display_name`, `description`, `enabled`, `stability`
- `service_class()` → returns the existing service class
- `routes_classes()` → returns the existing route class(es)
- `catalog_entry()` → the entry currently hard-coded in `Stack__Catalog__Service`. **Move the literal data into the manifest. Verify shape unchanged via byte-for-byte comparison test.**
- `event_topics_emitted()` → declarative list (the actual emit calls happen in PR-4)
- `setup()` → wraps the existing service.setup() if any

For `prometheus` and `opensearch` (currently SOON / partially-implemented), the manifest declares `enabled=False, stability='experimental'`. Their inclusion here is structural — the registry knows about them.

### Tests

- `test__plugin__manifest_for_each_type__loads_via_registry`
- `test__catalog_entries__from_registry__match_existing_hard_coded_list` (regression test against current behaviour)

### Acceptance

- 6 new `plugin/` sub-packages exist, each with one manifest class.
- `Plugin__Registry().discover()` returns 4 enabled manifests (linux, docker, elastic, vnc) and skips 2 (prometheus disabled, opensearch disabled).
- Catalog data from the manifests matches what `Stack__Catalog__Service` currently produces (regression test).
- All existing tests still pass — `Fast_API__SP__CLI` is unchanged.

### Effort

**1–1.5 days.** Mostly typing — each manifest is ~30 lines. Care needed on catalog-entry parity (the regression test catches drift).

---

## PR-3 — Refactor Fast_API__SP__CLI and Stack__Catalog__Service to consume the registry

**Goal:** `Fast_API__SP__CLI.setup_routes()` becomes plugin-driven. Catalog service consumes registry. **No external behaviour change** — the same routes are mounted, the catalog endpoint returns the same shape.

### Files touched

- `sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py` — replace per-service fields with `plugin_registry: Plugin__Registry`. `setup()` calls `plugin_registry.discover().setup_all()`. `setup_routes()` iterates `plugin_registry.all_routes_classes()`.
- `sgraph_ai_service_playwright__cli/catalog/service/Stack__Catalog__Service.py` — replace per-service fields with `plugin_registry: Plugin__Registry`. `list_types()` returns `plugin_registry.all_catalog_entries()`. `list_all_stacks()` iterates manifests and asks each service.

### Tests touched

- `tests/unit/sgraph_ai_service_playwright__cli/fast_api/test_Fast_API__SP__CLI.py`:
  - Existing `test_*_routes_are_mounted` tests still pass (regression).
  - New `test__plugin_registry__loaded_at_startup`
  - New `test__env_var_override__disables_plugin__routes_404` (set `PLUGIN__VNC__ENABLED=false`, restart app, verify `/vnc/stack` returns 404, catalog has no VNC entry)
- `tests/unit/sgraph_ai_service_playwright__cli/catalog/service/test_Stack__Catalog__Service.py`:
  - Existing tests: catalog returns 4 entries with expected names — still pass
  - New `test__list_types__delegates_to_plugin_registry`
  - New `test__list_all_stacks__iterates_plugin_registry__no_hard_coded_branches`

### Acceptance

- `Fast_API__SP__CLI.setup_routes()` is ≤ 10 lines.
- `grep -E "from sgraph_ai_service_playwright__cli\.(linux|docker|elastic|vnc|prometheus|opensearch)" sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py` returns zero hits.
- Setting `PLUGIN__VNC__ENABLED=false` env var → `/vnc/stack` returns 404, `/catalog/types` has no VNC entry, no errors in startup logs.
- All existing tests pass.
- Run the UI against the refactored backend — admin dashboard renders identically.

### Effort

**0.5–1 day.** The refactor is small (~50 lines net change) but needs careful test verification. The end-to-end UI smoke test catches anything subtle.

---

## PR-4 — Wire emit calls + listener tests

**Goal:** every existing `create_stack` / `delete_stack` success path emits its event. Tests verify the events fire with the right payload.

### Files touched

For each service in `linux/`, `docker/`, `elastic/`, `vnc/`, `prometheus/` (when enabled):

- Add at the success path of `create_stack`: `event_bus.emit('{type}:stack.created', Schema__Stack__Event(...))`
- Add at the success path of `delete_stack`: `event_bus.emit('{type}:stack.deleted', Schema__Stack__Event(...))`

That's ~10 lines of changes per service × 5 services = ~50 lines.

### Tests added

For each service:
- `test__create_stack__emits_event__with_correct_payload` — set up a listener, call create, assert listener received expected payload
- `test__create_stack__failure__does_not_emit` — make create fail, assert no event
- `test__delete_stack__emits_event` — same shape

Plus integration test in core:
- `test__cross_plugin__listener_in_audit_observes_create_in_vnc` — scaffolds the future audit-plugin pattern even though no audit plugin exists yet

### Acceptance

- For every existing type, creating and deleting a stack causes the corresponding `*:stack.created` / `*:stack.deleted` event to fire.
- Tests cover the happy path and failure path (no event on failure).
- The cross-plugin listener test passes — proves a non-emitter can observe an emitter's events without importing the emitter.

### Effort

**0.5–1 day.** Small targeted change in each service; the test scaffolding is the bulk.

---

## PR-5 — Neko stub plugin + experiment scaffolding

**Goal:** new `neko/` plugin folder. Manifest with `enabled=False`. Stub service. Empty routes returning 501. Experiment task documentation.

### Files created

```
sgraph_ai_service_playwright__cli/neko/
├── __init__.py
├── plugin/
│   ├── __init__.py
│   └── Plugin__Manifest__Neko.py
├── service/
│   ├── __init__.py
│   └── Neko__Service.py                  # stub — see doc 04
├── fast_api/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       └── Routes__Neko__Stack.py        # empty router; routes return 501
├── schemas/
│   ├── __init__.py
│   └── Schema__Neko__Stack__Info.py      # stub
└── docs/
    ├── README.md                         # points to brief doc 04
    ├── experiment-results.md             # template (filled in by future experiment session)
    └── tasks/
        ├── T1__kibana-discover.md
        ├── T2__mitmweb-flows.md
        ├── T3__kibana-dashboard.md
        ├── T4__kql-typing.md
        ├── T5__multi-viewer.md
        ├── T6__network-blip.md
        └── T7__iframe-embed.md
```

Plus `Enum__Stack__Type.NEKO = 'neko'` added to the existing enum.

Plus `'neko'` added to `Plugin__Registry.PLUGIN_FOLDERS`.

### Tests

- `test__neko__plugin_manifest__enabled_false__skipped_by_registry`
- `test__neko__plugin_manifest__force_enabled__service_calls_raise_NotImplementedError`
- `test__neko__catalog_entry__available_false__shows_as_SOON`

### Acceptance

- The Neko plugin folder exists with the structure above.
- Default registry discovery skips Neko (enabled=False); `core:plugin.skipped` event fires with reason='manifest-disabled'.
- If Neko is force-enabled (e.g. via `PLUGIN__NEKO__ENABLED=true` — though this still doesn't make sense since the manifest itself says enabled=False, but for completeness)… actually no. This PR confirms env-override only works to *disable* a plugin, not to *enable* a manifest-disabled one. Document this behaviour.
- The 7 task documents exist as markdown templates.
- `experiment-results.md` is a template with the measurement table empty.

### Effort

**0.5 day.** The bulk is the experiment task documentation, which is mostly copying/refining doc 04's task descriptions.

---

## What's NOT in this brief's PRs

- ❌ Per-instance FastAPI containers, AMI changes, instance-side API key generation. **See doc 03.**
- ❌ Vault-as-event-bus implementation. **See doc 03.**
- ❌ The Neko Docker image, EC2 user-data for Neko, the actual experiment run.
- ❌ A formal `Plugin__Service__Base` interface for services. The protocol-by-attribute pattern (`hasattr(service, 'list_stacks')`) is sufficient for now.
- ❌ Hot-reload of plugins. Disable requires a redeploy/restart.
- ❌ A plugin marketplace, dynamic plugin upload, etc.
- ❌ Cross-plugin event globs (`*:stack.created`). Listeners subscribe to specific events.

---

## Final acceptance — across the full brief

When all 5 PRs are merged, a reviewer should be able to confirm:

1. Six existing types each have a `plugin/` sub-package with a manifest.
2. `Plugin__Registry` discovers, loads, and exposes them.
3. `Fast_API__SP__CLI.setup_routes()` is ≤ 10 lines.
4. Disabling a plugin via env var → its routes 404, its catalog entry is gone.
5. `Stack__Catalog__Service.list_types()` returns entries from the registry, not hard-coded.
6. `Event__Bus` exists with `emit` / `on` / `off` / `reset`.
7. Each existing type's create/delete success path fires its event.
8. `core:plugin.loaded` and `core:plugin.skipped` fire at startup.
9. A new `neko/` plugin folder exists, manifest disabled, service stub, experiment docs.
10. No cross-plugin imports — `grep` confirms.
11. UI smoke test against the refactored backend works identically to before.

If any fails, the brief is not done.
