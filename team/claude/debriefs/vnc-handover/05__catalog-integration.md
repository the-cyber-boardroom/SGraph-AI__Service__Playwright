# `sp vnc` — Catalog integration gap

The `Stack__Catalog__Service` (under `cli/catalog/`) is the cross-section enumeration helper backing `GET /catalog/types` and `GET /catalog/stacks`. It already advertises `vnc` and `opensearch` in the **catalog metadata**, but does NOT compose those services in the **runtime listing**.

## What works

`cli/catalog/enums/Enum__Stack__Type.py`:

```python
class Enum__Stack__Type(str, Enum):
    LINUX      = 'linux'
    DOCKER     = 'docker'
    ELASTIC    = 'elastic'
    OPENSEARCH = 'opensearch'
    VNC        = 'vnc'
    # PROMETHEUS missing — see "What's missing" below
```

`cli/catalog/service/Stack__Catalog__Service__Entries.py` has `entry__opensearch()` and `entry__vnc()` — these populate the OpenAPI catalog entries returned by `GET /catalog/types`.

## What doesn't work — `list_all_stacks`

`Stack__Catalog__Service.list_all_stacks(type_filter=None)` is supposed to enumerate every live stack across every section. Today it only iterates Linux / Docker / Elastic:

```python
# cli/catalog/service/Stack__Catalog__Service.py
class Stack__Catalog__Service(Stack__Catalog__Service__Entries):
    linux_service   : Linux__Service
    docker_service  : Docker__Service
    elastic_service : Elastic__Service
    # opensearch_service / prometheus_service / vnc_service all missing

    def list_all_stacks(self, type_filter=None):
        # iterates linux_service.list_stacks() / docker_service.list_stacks() / elastic_service.list_stacks()
        # ...
        # NO branch for OPENSEARCH / PROMETHEUS / VNC
```

So `GET /catalog/stacks?type=vnc` returns an empty list even when there are real `sp vnc` instances running.

## What's missing

1. **`Enum__Stack__Type.PROMETHEUS = 'prometheus'`** — currently the enum doesn't have it. `entry__prometheus()` doesn't exist either.
2. **Service composition fields:**
   ```python
   class Stack__Catalog__Service(Stack__Catalog__Service__Entries):
       linux_service      : Linux__Service
       docker_service     : Docker__Service
       elastic_service    : Elastic__Service
       opensearch_service : OpenSearch__Service                    # NEW
       prometheus_service : Prometheus__Service                    # NEW
       vnc_service        : Vnc__Service                           # NEW
   ```
3. **Three new branches in `list_all_stacks`:**
   ```python
   if type_filter in (None, OPENSEARCH):
       for info in self.opensearch_service.list_stacks('').stacks:
           summaries.append(Schema__Stack__Summary(
               type_id=OPENSEARCH, stack_name=str(info.stack_name),
               state=info.state.value, public_ip=str(info.public_ip),
               region=str(info.region), instance_id=str(info.instance_id),
               uptime_seconds=info.uptime_seconds))
   if type_filter in (None, PROMETHEUS):
       # same shape
   if type_filter in (None, VNC):
       # same shape
   ```
4. **`get_catalog()` already iterates `entry__opensearch` + `entry__vnc`** — just add `entry__prometheus` once it exists.

## Where the `setup()` hook needs to land

`Stack__Catalog__Service` is itself a Type_Safe — its sub-service fields auto-init to fresh instances (no `setup()` chain by default). When wiring through `Fast_API__SP__CLI`, the parent's `setup()` should call:

```python
self.catalog_service.opensearch_service.setup()
self.catalog_service.prometheus_service.setup()
self.catalog_service.vnc_service.setup()
```

Or — cleaner — give `Stack__Catalog__Service` its own `setup()` that recursively sets up its sub-services. This matches the existing pattern where `Vnc__Service.setup()` lazy-wires its 8 helpers.

## Tests to update

`tests/unit/sgraph_ai_service_playwright__cli/catalog/`:
- `test_Enum__Stack__Type.py` — add `PROMETHEUS`
- `test_Stack__Catalog__Service.py` — extend the "list all stacks" coverage to include the three new sections (in-memory `_Fake_*__Service` subclasses already used elsewhere in the codebase)
- `test_Routes__Stack__Catalog.py` — add expectations for `?type=opensearch` / `?type=prometheus` / `?type=vnc` responses

## Why this matters for the UI

The MVP UI from v0.1.101 (`team/claude/debriefs/2026-04-29__v0.1.101__mvp-admin-user-ui.md`) drives its dashboard from `GET /catalog/stacks`. Until OpenSearch / Prometheus / VNC stacks show up there, they're invisible to the admin/user UIs.

## Suggested order of work for the next session

1. Wire `Routes__OpenSearch__Stack`, `Routes__Prometheus__Stack`, `Routes__Vnc__Stack`, `Routes__Vnc__Flows` into `Fast_API__SP__CLI` (see [04__missing-wiring.md](./04__missing-wiring.md))
2. Add `PROMETHEUS` to `Enum__Stack__Type` + `entry__prometheus()` in `Stack__Catalog__Service__Entries`
3. Extend `Stack__Catalog__Service` with the 3 new service fields + 3 branches in `list_all_stacks`
4. Update tests
5. Sanity check via local UI (admin dashboard should now show OpenSearch / Prometheus / VNC tiles populated with live stacks)
