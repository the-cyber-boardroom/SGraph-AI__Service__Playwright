# v0.22.19 — Backend Plugin Architecture

**Brief:** Backend plugin architecture for SP-CLI compute types
**Status:** PROPOSED — ready for Sonnet pickup
**Target version:** v0.22.19 (slice numbering will land in `team/comms/briefs/v0.22.19__backend-plugin-architecture/`)
**Date drafted:** 2026-04-29
**Author:** Architect (Opus session, agreed with project lead)
**Audience:** Sonnet (backend track), Architect, DevOps
**Source memo:** `team/humans/dinis_cruz/briefs/v0.22.19__arch-brief__backend-plugin-architecture.md`
**Frontend counterpart:** `v0.22.19__fractal-frontend-ui/` (separate Sonnet track)

---

## What this brief is

A surgical, additive change to make the existing backend a real **plugin system** — without rewriting what already works. Today's `sgraph_ai_service_playwright__cli/` already has `linux/`, `docker/`, `elastic/`, `vnc/`, `prometheus/`, `opensearch/` each in their own folder with parallel substructure. They behave like plugins but aren't *registered* like plugins — they're hand-imported and hand-mounted in `Fast_API__SP__CLI`. This brief adds the registration layer on top of the existing folders.

After this brief lands:

1. Each compute type's folder additionally contains a **plugin manifest** describing its routes, CLI commands, catalog entry, and `enabled` flag.
2. A new **`Plugin__Registry`** scans the folders, reads manifests, and mounts only enabled plugins. `Fast_API__SP__CLI.setup_routes()` becomes ~3 lines.
3. A new **in-process event bus** lets plugins emit and listen for events with no inter-plugin imports. Existing direct method calls between services stay as they are.
4. A new **Neko plugin** is added as a research stub (not a working compute type yet) so the brief produces a measurement rig for the Neko-vs-VNC decision.

After this brief explicitly does **NOT** land:

- ❌ Per-instance FastAPI containers with random API keys. **This is its own brief** (forward-looking arch doc included; see `03__forward-roadmap.md`). The reasoning is below.
- ❌ Rewriting any existing service class.
- ❌ Splitting shared primitives (`Caller__IP__Detector`, AWS clients) further than they already are. The existing section-localised pattern is preserved.
- ❌ Cross-process event buses (Redis, EventBridge). In-process only for MVP.
- ❌ Auth changes (X-API-Key middleware stays).
- ❌ A plugin marketplace, dynamic plugin upload, or anything resembling extension installation by users.

## How to read this series

| # | Doc | Read when | Approx size |
|---|---|---|---|
| `00` | [`00__README__backend-plugin-architecture.md`](00__README__backend-plugin-architecture.md) *(this file)* | First — orientation | ~150 lines |
| `01` | [`plugin-registry-design.md`](01__plugin-registry-design.md) | When implementing the registry, manifest, or refactoring `Fast_API__SP__CLI` | ~350 lines |
| `02` | [`event-bus-design.md`](02__event-bus-design.md) | When implementing the event bus or wiring emit/listen | ~250 lines |
| `03` | [`forward-roadmap.md`](03__forward-roadmap.md) | When planning the next architectural step (per-instance FastAPI, vault-as-bus). **No implementation in this brief.** | ~200 lines |
| `04` | [`neko-experiment.md`](04__neko-experiment.md) | When evaluating Neko vs VNC | ~250 lines |
| `05` | [`implementation-plan.md`](05__implementation-plan.md) | When picking the next PR to ship | ~200 lines |

Total ~1,400 lines.

## Key decisions (made — do not relitigate)

| # | Decision | Rationale |
|---|---|---|
| 1 | **Plugin isolation is graduated, not absolute.** Existing types stay in their current folders. Registration layer added on top. New types (Neko, future ones) follow the full plugin shape from day one. | The existing types were intentionally section-localised over many slices; pulling them apart further is carving where there's no joint. Adding a manifest + registry is a one-day change. Rewriting the existing services is a multi-week change with no payoff. |
| 2 | **Per-instance FastAPI container is its own future brief.** Mentioned in `03__forward-roadmap.md` only. | Net new work on every existing AMI. Standardised instance control plane is potentially excellent but doesn't belong in a structural-refactor brief. |
| 3 | **In-process event bus only.** No Redis, no EventBridge, no cross-process pub/sub. | MVP scope. Lambda-deployed FastAPI; in-process is sufficient. Vault-as-bus is on the roadmap (forward doc). |
| 4 | **Plugin manifest is Python (`Plugin__Manifest__{Type}`), not JSON.** Type-Safe schema. | Repo conventions: all schemas are `Type_Safe` from osbot-utils. JSON manifests would force runtime parsing for things the type system already validates. We can later add a tool that exports manifest → JSON for a UI. |
| 5 | **`enabled` flag is on the plugin manifest, settable per-deployment via env var override.** | Operators can disable a plugin without redeploying or editing source. Default is `True` for stable plugins, `False` for experimental ones. |
| 6 | **Event names follow `{plugin}:{noun}.{verb}` convention.** E.g., `linux:stack.created`, `vnc:stack.deleted`, `core:plugin.loaded`. | The existing UI uses `{family}:{action}` (`vault:connected`, `sp-cli:vault-bus:read-started`); keep the same pattern but add the noun/verb structure for backend events to match the architectural ambition (events = facts about resources). |
| 7 | **Catalog entry generation is owned by the plugin manifest.** `Stack__Catalog__Service.list_types()` becomes "ask the registry for all enabled plugin manifests, collect their `catalog_entry()` outputs." | Today the catalog service hard-codes the four types. Moving the catalog-entry creation to each plugin's manifest closes the loop: enabling a plugin adds its catalog entry automatically. |
| 8 | **Neko ships as a stub** — manifest, empty service, empty routes, `enabled=False`, integration tests skipped. | Its purpose this slice is to (a) validate that the plugin shape works for a brand-new type, and (b) provide the scaffolding for the experiment doc. The actual Neko evaluation is its own follow-up. |

## Layering rules (non-negotiable)

1. **Plugin code never imports from another plugin's module.** All cross-plugin communication via the event bus or via the catalog service.
2. **Plugin manifests are pure data + factory methods.** No business logic in a manifest.
3. **The registry is the only thing that imports plugin modules.** `Fast_API__SP__CLI` imports the registry, not the plugins.
4. **Plugin `enabled=False` means the plugin module is *not even imported*.** This way, broken or in-progress plugins can ship `enabled=False` without breaking startup.
5. **Event bus is in-process only.** No HTTP, no Redis, no cross-Lambda. If we need cross-process events later, vault-as-bus is the planned path.
6. **No event guarantees delivery.** Listeners are best-effort. If an emitter cares about "did the listener succeed?", that's a method call, not an event.
7. **All schemas extend `Type_Safe`** (existing repo rule).

## Acceptance for "this brief is done"

A reviewer should be able to confirm all of these:

1. Each existing compute type (`linux/`, `docker/`, `elastic/`, `vnc/`, `prometheus/`, `opensearch/`) has a `plugin/Plugin__Manifest__{Name}.py` declaring its routes, service, catalog entry, and enabled flag.
2. A new `Plugin__Registry` class discovers, instantiates, and exposes manifests at startup.
3. `Fast_API__SP__CLI.setup_routes()` is ≤10 lines and contains no per-plugin route imports.
4. Setting an env var like `PLUGIN__VNC__ENABLED=false` and restarting → all `/vnc/*` routes 404, VNC catalog entry disappears, no error.
5. `Stack__Catalog__Service.list_types()` returns entries dynamically from enabled plugins (no hard-coded type list).
6. An `Event__Bus` exists with `emit(event_name, payload)` and `on(event_name, handler)`. In-process. Best-effort. Silent drop if no listener.
7. At minimum these events fire: `linux:stack.created`, `linux:stack.deleted`, `docker:stack.created`, `docker:stack.deleted`, `vnc:stack.created`, `vnc:stack.deleted`, `elastic:stack.created`, `elastic:stack.deleted`. Each carries a `Schema__Stack__Event` payload (defined in core).
8. A `core:plugin.loaded` and `core:plugin.skipped` event fires per plugin at startup.
9. A new `neko/` plugin folder exists with manifest (`enabled=False`), a stub service that raises `NotImplementedError`, and the experiment scaffolding from doc 04.
10. Tests cover: (a) registry with all plugins enabled, (b) registry with one plugin disabled (route 404, catalog gone), (c) event bus emit-with-no-listener (silent), (d) event bus emit-with-listener (delivered).
11. `grep -r "from sgraph_ai_service_playwright__cli.linux" sgraph_ai_service_playwright__cli/{docker,elastic,vnc,prometheus,opensearch,neko}/ ` returns zero hits (no cross-plugin imports).
12. The `forward-roadmap.md` doc is checked in but no code from it is implemented this slice.

If any fails, the brief is not done.

## Effort estimate

Roughly 4–6 dev-days for one backend developer:

- 0.5d — `Plugin__Manifest__Base` + `Plugin__Registry` + tests
- 1d — Migrate the 6 existing types to manifests + register
- 0.5d — Refactor `Fast_API__SP__CLI` + `Stack__Catalog__Service` to consume registry
- 0.5d — `Event__Bus` + tests
- 0.5d — Wire emit calls into create/delete paths for all 6 existing types
- 0.5d — Add Neko stub plugin + manifest + skip-marked tests
- 0.5d — Doc 04 (Neko experiment plan) + scaffolding
- 0.5d — `core:plugin.loaded` / `core:plugin.skipped` events + env var override + integration tests
- 0.5d — Polish: docstrings, ensure `Type_Safe` everywhere, debug log for plugin discovery

## What ships after this brief

In probable priority order:

1. **Neko evaluation experiment** (per doc 04). One-week experiment, results doc, go/no-go decision on Neko-as-default.
2. **Per-instance FastAPI container** (per doc 03 forward roadmap). Multi-week piece.
3. **Vault-as-event-bus** for cross-process / cross-Lambda event durability and audit.
4. **Plugin manifest UI** in the admin dashboard (Settings panel — see frontend brief).
5. **Frontend plugin discovery** to consume the catalog dynamically (already partly in place).

Each gets its own brief.

## Coordination with the frontend track

The frontend brief (`v0.22.19__fractal-frontend-ui/`) is being implemented in parallel. **The point of contact between the two is the catalog endpoint** — `GET /catalog/types` returns the list of enabled plugins with their metadata. The frontend reads this and renders a card per plugin. As long as this endpoint's response shape is stable, the two tracks don't block each other.

The only **shared schema** between the two briefs is `Schema__Stack__Type__Catalog__Entry` — already existing in the repo, this brief preserves it. New optional fields can be added (e.g. `stability: 'stable'|'experimental'|'deprecated'`); deletions or renames need cross-brief coordination.

The backend brief does NOT add new instance management endpoints; the existing `/{type}/stack`, `/{type}/stacks`, `/{type}/stack/{name}` etc. all stay. Plugin migration is purely structural — same wire protocol, different mounting mechanism.
