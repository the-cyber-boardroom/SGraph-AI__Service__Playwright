# 02 — Backend Changes

**Status:** PROPOSED
**Read after:** `README.md`, `01__mvp-scope-and-flows.md`
**Audience:** Sonnet implementing the Python side
**Verified against:** `dev` HEAD `7e72431`, package version `v0.1.100`, repo version `v0.1.101`

---

## What this doc gives you

Three PR-sized backend changes, in order. Each has:

- The exact files to touch.
- The exact files to create.
- The exact tests to add.
- An acceptance criterion that can be verified with one or two commands.

Total: ~2 dev-days for one developer.

## Pre-flight

Before writing any code:

```bash
git fetch origin dev && git merge origin/dev
git checkout -b claude/mvp-provisioning-ui-{session-id}

# Run the existing test suite, baseline-clean
pytest tests/unit/sgraph_ai_service_playwright__cli/ -x

# Boot the existing app to confirm baseline
python -m scripts.run_sp_cli  # serves on http://localhost:8080
curl -s http://localhost:8080/openapi.json | jq '.paths | keys'
# Expected today: routes under /ec2/playwright/* and /observability/*
```

Read these before coding (they're the patterns you'll mirror):

| File | Why |
|---|---|
| `sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py` | The class you're mounting routes on |
| `sgraph_ai_service_playwright__cli/linux/fast_api/routes/Routes__Linux__Stack.py` | Routes to mount (PR-1); template for new routes (PR-3) |
| `sgraph_ai_service_playwright__cli/docker/fast_api/routes/Routes__Docker__Stack.py` | Same |
| `tests/unit/sgraph_ai_service_playwright__cli/opensearch/fast_api/routes/test_Routes__OpenSearch__Stack.py` | The exact testing pattern — `_Fake_Service` real-subclass approach, no mocks |
| `sgraph_ai_service_playwright__cli/elastic/service/Elastic__Service.py` | Service whose lifecycle methods you're exposing in PR-3 |

## PR-1 — Mount linux + docker routes on `Fast_API__SP__CLI`

**Goal:** make `/linux/*` and `/docker/*` callable via HTTP. The route classes already exist; they just aren't wired in.

### Files touched

**`sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py`** — add 4 imports, 2 type-safe attrs, 2 `add_routes` calls.

```python
# ─── new imports
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                  import Linux__Service
from sgraph_ai_service_playwright__cli.linux.fast_api.routes.Routes__Linux__Stack    import Routes__Linux__Stack
from sgraph_ai_service_playwright__cli.docker.service.Docker__Service                import Docker__Service
from sgraph_ai_service_playwright__cli.docker.fast_api.routes.Routes__Docker__Stack  import Routes__Docker__Stack


class Fast_API__SP__CLI(Fast_API):
    ec2_service           : Ec2__Service
    observability_service : Observability__Service
    linux_service         : Linux__Service                                           # NEW — Type_Safe auto-initialises
    docker_service        : Docker__Service                                          # NEW — same

    # __init__ unchanged
    # setup() unchanged

    def setup_routes(self):
        self.add_routes(Routes__Ec2__Playwright , service=self.ec2_service          )
        self.add_routes(Routes__Observability   , service=self.observability_service)
        self.add_routes(Routes__Linux__Stack    , service=self.linux_service       )    # NEW
        self.add_routes(Routes__Docker__Stack   , service=self.docker_service      )    # NEW
```

### Files created

None. Both route classes already exist with full route definitions.

### Tests

**`tests/unit/sgraph_ai_service_playwright__cli/fast_api/test_Fast_API__SP__CLI.py`** — extend the existing test file (or create the section if absent) to assert the new routes mount.

```python
def test_linux_routes_are_mounted():
    app   = Fast_API__SP__CLI().setup().app()
    paths = {route.path for route in app.routes}
    assert '/linux/stacks'                 in paths                                  # GET list
    assert '/linux/stack/{name}'           in paths                                  # GET info + DELETE
    assert '/linux/stack'                  in paths                                  # POST create
    assert '/linux/stack/{name}/health'    in paths                                  # GET health


def test_docker_routes_are_mounted():
    app   = Fast_API__SP__CLI().setup().app()
    paths = {route.path for route in app.routes}
    assert '/docker/stacks'                in paths
    assert '/docker/stack/{name}'          in paths
    assert '/docker/stack'                 in paths
    assert '/docker/stack/{name}/health'   in paths
```

This is mounting verification only — not full TestClient drive-throughs. Per-route TestClient tests for linux/docker are a follow-up housekeeping task tracked separately (mirror the `test_Routes__OpenSearch__Stack.py` pattern when picked up).

### Acceptance

```bash
python -m scripts.run_sp_cli &
sleep 2
curl -s http://localhost:8080/openapi.json | jq '.paths | keys[]' | grep -E '^"/(linux|docker)/'
```

Expected: 10 paths (5 linux + 5 docker). Existing paths unchanged.

### Effort estimate

**0.5 day** including tests and a small TestClient smoke-test of one linux endpoint to confirm wiring (e.g. `GET /linux/stacks` returns a `Schema__Linux__List` shape).

---

## PR-2 — `catalog/` sub-package and `Routes__Stack__Catalog`

**Goal:** give the UI one cross-section read API. Two endpoints today, easy to extend.

This is the only genuinely new piece of orchestration in the brief. It composes the existing per-section services; it does not replace them and it does not touch AWS directly (it goes through the per-section services, which go through their own `*__AWS__Client` boundaries).

### Folder layout (new)

```
sgraph_ai_service_playwright__cli/catalog/
├── __init__.py                                      # empty
├── enums/
│   ├── __init__.py                                  # empty
│   └── Enum__Stack__Type.py                         # LINUX, DOCKER, ELASTIC, OPENSEARCH, VNC
├── primitives/
│   └── __init__.py                                  # empty (reuses ec2 + observability primitives)
├── schemas/
│   ├── __init__.py                                  # empty
│   ├── Schema__Stack__Type__Catalog__Entry.py       # one type's metadata
│   ├── Schema__Stack__Type__Catalog.py              # the list-of-types response
│   ├── Schema__Stack__Summary.py                    # one running stack, type-agnostic
│   └── Schema__Stack__Summary__List.py              # the list-of-stacks response
├── collections/
│   ├── __init__.py                                  # empty
│   ├── List__Schema__Stack__Type__Catalog__Entry.py
│   └── List__Schema__Stack__Summary.py
├── service/
│   ├── __init__.py                                  # empty
│   └── Stack__Catalog__Service.py                   # composes per-section services
└── fast_api/
    ├── __init__.py                                  # empty
    └── routes/
        ├── __init__.py                              # empty
        └── Routes__Stack__Catalog.py
```

### Schemas

**`Enum__Stack__Type`** — one file, one enum, five values. Names match the URL section names (`linux`, `docker`, `elastic`, `opensearch`, `vnc`).

```python
# Enum__Stack__Type.py
from enum import Enum


class Enum__Stack__Type(Enum):
    LINUX      = 'linux'
    DOCKER     = 'docker'
    ELASTIC    = 'elastic'
    OPENSEARCH = 'opensearch'
    VNC        = 'vnc'
```

**`Schema__Stack__Type__Catalog__Entry`** — one entry per stack type.

```python
class Schema__Stack__Type__Catalog__Entry(Type_Safe):
    type_id                : Enum__Stack__Type                                       # canonical id
    display_name           : Safe_Str__Text                                          # "Bare Linux", "Docker host", etc.
    description            : Safe_Str__Text
    available              : bool                  = False                           # false → "coming soon" tile
    default_instance_type  : Safe_Str__Text                                          # "t3.medium"
    default_max_hours      : int                   = 4                               # auto-stop default
    expected_boot_seconds  : int                   = 60                              # for the progress bar
    create_endpoint_path   : Safe_Str__Text                                          # "/linux/stack" etc.
    list_endpoint_path     : Safe_Str__Text                                          # "/linux/stacks"
    info_endpoint_path     : Safe_Str__Text                                          # "/linux/stack/{name}"
    delete_endpoint_path   : Safe_Str__Text                                          # "/linux/stack/{name}"
    health_endpoint_path   : Safe_Str__Text                                          # "/linux/stack/{name}/health"
```

Endpoint paths are surfaced as data so the UI doesn't hard-code them — adding a sixth type (or moving an existing path) is a server-side change only.

**`Schema__Stack__Type__Catalog`** — the response shape for `GET /catalog/types`.

```python
class Schema__Stack__Type__Catalog(Type_Safe):
    entries: List__Schema__Stack__Type__Catalog__Entry
```

**`Schema__Stack__Summary`** — one running stack across any section.

```python
class Schema__Stack__Summary(Type_Safe):
    type_id        : Enum__Stack__Type
    stack_name     : Safe_Str__Text                                                  # cross-type, so use Safe_Str__Text not the per-type primitives
    state          : Safe_Str__Text                                                  # rendered name of the per-type Enum__*__Stack__State
    public_ip      : Safe_Str__Text                                                  # may be empty during boot
    region         : Safe_Str__Text
    instance_id    : Safe_Str__Text
    uptime_seconds : int = 0
```

**`Schema__Stack__Summary__List`** — response shape for `GET /catalog/stacks`.

```python
class Schema__Stack__Summary__List(Type_Safe):
    stacks: List__Schema__Stack__Summary
```

**Collections**: per the codebase's one-class-per-file rule, both `List__*` are dedicated files. Mirror the shape of `List__Ec2__Instance__Info` for the file template.

### `Stack__Catalog__Service`

This is the only new logic. It owns:

1. The static catalog data (which types exist, their display metadata, their `available` flags).
2. The cross-section list, which calls each *available* per-section service's `list_stacks()` and normalises the results into `Schema__Stack__Summary` entries.

```python
# service/Stack__Catalog__Service.py — sketch (not literal final code)

class Stack__Catalog__Service(Type_Safe):
    linux_service        : Linux__Service                                            # Type_Safe auto-initialises
    docker_service       : Docker__Service
    elastic_service      : Elastic__Service                                          # used by both this PR and PR-3

    def get_catalog(self) -> Schema__Stack__Type__Catalog:
        entries = List__Schema__Stack__Type__Catalog__Entry()
        entries.append(self._entry__linux     ())
        entries.append(self._entry__docker    ())
        entries.append(self._entry__elastic   ())
        entries.append(self._entry__opensearch())
        entries.append(self._entry__vnc       ())
        return Schema__Stack__Type__Catalog(entries=entries)

    def list_all_stacks(self,
                        type_filter: Enum__Stack__Type = None
                       ) -> Schema__Stack__Summary__List:
        summaries = List__Schema__Stack__Summary()
        if type_filter is None or type_filter == Enum__Stack__Type.LINUX:
            for info in self.linux_service.list_stacks().stacks:
                summaries.append(self._summary__from_linux(info))
        if type_filter is None or type_filter == Enum__Stack__Type.DOCKER:
            for info in self.docker_service.list_stacks().stacks:
                summaries.append(self._summary__from_docker(info))
        if type_filter is None or type_filter == Enum__Stack__Type.ELASTIC:
            for info in self.elastic_service.list_stacks().stacks:
                summaries.append(self._summary__from_elastic(info))
        return Schema__Stack__Summary__List(stacks=summaries)

    # _entry__linux, _entry__docker, _entry__elastic build catalog entries with available=True
    # _entry__opensearch, _entry__vnc build entries with available=False (the "coming soon" tiles)
    # _summary__from_linux / _docker / _elastic do the per-type → Schema__Stack__Summary conversion
```

**Catalog values for the MVP** (what each `_entry__*` returns):

| Type | available | display_name | default_instance_type | expected_boot_seconds |
|---|---|---|---|---|
| LINUX | `True` | "Bare Linux" | `t3.medium` | 60 |
| DOCKER | `True` | "Docker host" | `t3.medium` | 600 |
| ELASTIC | `True` | "Elastic + Kibana" | `t3.medium` | 90 |
| OPENSEARCH | `False` | "OpenSearch + Dashboards" | `t3.medium` | 120 |
| VNC | `False` | "VNC bastion (browser-in-browser)" | `t3.medium` | 90 |

Endpoint paths are derived from the type id: `/{type_id.value}/stacks`, `/{type_id.value}/stack`, `/{type_id.value}/stack/{name}`, `/{type_id.value}/stack/{name}/health`. There's a small helper to build them; one place to fix if the convention ever changes.

### `Routes__Stack__Catalog`

Mirrors the shape of `Routes__Linux__Stack`. Tag is `catalog`.

```python
# fast_api/routes/Routes__Stack__Catalog.py

class Routes__Stack__Catalog(Fast_API__Routes):
    tag     : str                       = 'catalog'
    service : Stack__Catalog__Service                                                # Injected

    def types(self) -> dict:                                                          # GET /catalog/types
        return self.service.get_catalog().json()
    types.__route_path__ = '/types'

    def stacks(self, type: str = '') -> dict:                                         # GET /catalog/stacks?type=linux
        type_filter = None
        if type:
            try:
                type_filter = Enum__Stack__Type(type)                                 # raises ValueError for unknown — handled by 422
            except ValueError:
                raise HTTPException(status_code=422, detail=f'unknown stack type: {type!r}')
        return self.service.list_all_stacks(type_filter=type_filter).json()
    stacks.__route_path__ = '/stacks'

    def setup_routes(self):
        self.add_route_get(self.types )
        self.add_route_get(self.stacks)
```

### Mount on `Fast_API__SP__CLI`

```python
# Fast_API__SP__CLI.py — extend setup_routes()

self.add_routes(Routes__Stack__Catalog, service=self.catalog_service)
```

And the new attribute:

```python
catalog_service : Stack__Catalog__Service                                            # Type_Safe auto-initialises
```

`Stack__Catalog__Service` itself has Type_Safe attrs for the per-section services it composes; those auto-initialise too. `Fast_API__SP__CLI` ends up with the catalog service initialised once at app construction and shared across requests.

### Tests

**`tests/unit/sgraph_ai_service_playwright__cli/catalog/`** — mirror the test layout the package has.

- `tests/unit/sgraph_ai_service_playwright__cli/catalog/schemas/` — one test per schema (round-trip `.json()` and `.from_json()`).
- `tests/unit/sgraph_ai_service_playwright__cli/catalog/service/test_Stack__Catalog__Service.py` — uses real `_Fake_Linux__Service`, `_Fake_Docker__Service`, `_Fake_Elastic__Service` subclasses (the `osbot-fast-api` real-subclass pattern from `test_Routes__OpenSearch__Stack.py`) returning scripted `Schema__*__List` data. Asserts:
  - `get_catalog()` returns 5 entries with the expected `available` flags
  - `list_all_stacks(type_filter=None)` returns the union, normalised
  - `list_all_stacks(type_filter=LINUX)` returns only linux entries
- `tests/unit/sgraph_ai_service_playwright__cli/catalog/fast_api/routes/test_Routes__Stack__Catalog.py` — TestClient against an `osbot-fast-api Fast_API` shell with the route mounted, hits `GET /catalog/types`, `GET /catalog/stacks`, `GET /catalog/stacks?type=linux`, `GET /catalog/stacks?type=banana` (expects 422).

Plus extending `test_Fast_API__SP__CLI.py`:

```python
def test_catalog_routes_are_mounted():
    app   = Fast_API__SP__CLI().setup().app()
    paths = {route.path for route in app.routes}
    assert '/catalog/types'  in paths
    assert '/catalog/stacks' in paths
```

### Acceptance

```bash
curl -s http://localhost:8080/catalog/types | jq '.entries | length'           # 5
curl -s http://localhost:8080/catalog/types | jq '.entries[] | {type_id, available}'
# linux/docker/elastic available, opensearch/vnc not

curl -s http://localhost:8080/catalog/stacks                                   # array, possibly empty
curl -s "http://localhost:8080/catalog/stacks?type=linux"                      # filtered
curl -s "http://localhost:8080/catalog/stacks?type=banana"                     # 422
```

### Effort estimate

**1 day** — the schemas and the service are straightforward; the bulk is following the one-class-per-file convention and writing the test scaffolding for the catalog package's own folder tree.

---

## PR-3 — `Routes__Elastic__Stack` (mirror linux/docker shape)

**Goal:** give the elastic service its lifecycle HTTP routes so the UI's elastic tile becomes live.

The Elastic service is the largest in the codebase (~50KB) and exposes many domain operations beyond the lifecycle (seed, wipe-seed, harden-kibana, AMI ops, saved-objects). **This PR exposes only the lifecycle subset.** Everything else stays CLI-only and is the subject of follow-up briefs.

### Files created

**`sgraph_ai_service_playwright__cli/elastic/fast_api/routes/Routes__Elastic__Stack.py`** — same shape as `Routes__Linux__Stack`, mapping to the same five operations.

```python
TAG__ROUTES_ELASTIC = 'elastic'


class Routes__Elastic__Stack(Fast_API__Routes):
    tag     : str               = TAG__ROUTES_ELASTIC
    service : Elastic__Service                                                       # Injected

    def list_stacks(self, region: str = '') -> dict:                                  # GET /elastic/stacks
        return self.service.list_stacks(region or DEFAULT_REGION).json()
    list_stacks.__route_path__ = '/stacks'

    def info(self, name: str, region: str = '') -> dict:                              # GET /elastic/stack/{name}
        result = self.service.get_stack_info(name, region or DEFAULT_REGION)
        if result is None:
            raise HTTPException(status_code=404, detail=f'no elastic stack matched {name!r}')
        return result.json()
    info.__route_path__ = '/stack/{name}'

    def create(self, body: Schema__Elastic__Create__Request) -> dict:                 # POST /elastic/stack
        return self.service.create_stack(body).json()
    create.__route_path__ = '/stack'

    def delete(self, name: str, region: str = '') -> dict:                            # DELETE /elastic/stack/{name}
        response = self.service.delete_stack(name, region or DEFAULT_REGION)
        if not response.deleted:
            raise HTTPException(status_code=404, detail=f'no elastic stack matched {name!r}')
        return response.json()
    delete.__route_path__ = '/stack/{name}'

    def health(self, name: str) -> dict:                                              # GET /elastic/stack/{name}/health
        return self.service.health(stack_name=name, check_ssm=True).json()
    health.__route_path__ = '/stack/{name}/health'

    def setup_routes(self):
        self.add_route_get   (self.list_stacks)
        self.add_route_get   (self.info       )
        self.add_route_post  (self.create     )
        self.add_route_delete(self.delete     )
        self.add_route_get   (self.health     )
```

**Two service-method-signature notes** — Sonnet should verify these against `Elastic__Service.py` before coding (the signatures differ slightly from linux/docker):

1. `Elastic__Service.get_stack_info(name, region)` — argument order is `(stack_name, region)`, not `(region, stack_name)` like linux/docker. Don't call it with positional kwargs in the wrong order.
2. `Elastic__Service.health(stack_name, password='', check_ssm=True)` — there is no `region` parameter on this signature. The route shape above passes `check_ssm=True` to match the linux/docker behaviour.

If either of these is materially different by the time PR-3 lands, the route adapts to the service. The brief follows the rule: **route is dumb, service shape wins.**

### Files touched

**`sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py`** — extend imports, attrs, mounts.

```python
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service                  import Elastic__Service
from sgraph_ai_service_playwright__cli.elastic.fast_api.routes.Routes__Elastic__Stack    import Routes__Elastic__Stack

# attribute
elastic_service : Elastic__Service

# in setup_routes
self.add_routes(Routes__Elastic__Stack, service=self.elastic_service)
```

**`Stack__Catalog__Service.py`** — already wired in PR-2; no change here.

### Tests

**`tests/unit/sgraph_ai_service_playwright__cli/elastic/fast_api/routes/test_Routes__Elastic__Stack.py`** — full TestClient pattern, mirroring `test_Routes__OpenSearch__Stack.py`:

- A `_Fake_Elastic__Service` real subclass that overrides `list_stacks`, `get_stack_info`, `create_stack`, `delete_stack`, `health` to return scripted Type_Safe responses.
- Tests for each route covering: happy path, 404 path (info / delete), 422 path (bad body shape).
- ~10 unit tests, no mocks, matches the OpenSearch test count.

Plus extending `test_Fast_API__SP__CLI.py`:

```python
def test_elastic_routes_are_mounted():
    app   = Fast_API__SP__CLI().setup().app()
    paths = {route.path for route in app.routes}
    assert '/elastic/stacks'              in paths
    assert '/elastic/stack/{name}'        in paths
    assert '/elastic/stack'               in paths
    assert '/elastic/stack/{name}/health' in paths
```

### Acceptance

```bash
curl -s http://localhost:8080/openapi.json | jq '.paths | keys[]' | grep '^"/elastic/'
# Expected: 4 paths (stacks, stack, stack/{name}, stack/{name}/health)
```

Plus a smoke test against a real AWS account if available — `POST /elastic/stack` with a minimal body, poll `GET /elastic/stack/{name}/health` until healthy, `DELETE /elastic/stack/{name}`. This mirrors what the user UI will do in the demo.

### Effort estimate

**1 day** — half a day for the route class itself (it's a port from the linux/docker template), half a day for the test harness (`_Fake_Elastic__Service` is more work than the OpenSearch one because the surface is bigger, even though we only override the lifecycle subset).

---

## Sequencing

```
   PR-1  ──► PR-2  ──► PR-3
   (mount)  (catalog) (elastic routes)
   0.5d     1d        1d
```

PR-1 unblocks the linux + docker tiles. PR-2 unblocks the entire UI (without `/catalog/`, the UI has nowhere to ask "what types exist?"). PR-3 makes the elastic tile go live.

The UI work in doc 03 can start in parallel with PR-1 (against a stub catalog) — but it can't end until PR-2 lands. Realistically, backend dev runs PR-1 → PR-2 → PR-3 over two days while UI dev is working in parallel; both meet at the integration point.

## What this brief does NOT include

These are deliberate omissions, each its own follow-up brief:

- **`Routes__OpenSearch__Stack` mounting on `Fast_API__SP__CLI`.** The catalogue currently includes opensearch as a "coming soon" tile so the UI surface is already correct. (Code check: opensearch routes may already be mounted — if so, flip the catalog `available` flag in a one-line PR. If not, that's a one-line PR plus a route-mount when you decide to.)
- **`Routes__Vnc__Stack`.** Depends on the `sp vnc` slice landing per `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`. That whole package is multi-day Dev work and out of scope for this brief.
- **Section-specific operations** (elastic seed/wipe, observability backup, ec2 mitm flows) — those routes don't exist yet and aren't needed for the demo.
- **`POST /catalog/stacks`** as a unified create endpoint that dispatches to the right per-section service — proposed by neither the catalog nor the UI design. The UI calls per-section endpoints directly. The catalog is read-only.
- **Full route-level test coverage for linux/docker.** Mounting tests in PR-1 are sufficient for the demo. Bringing those up to OpenSearch parity (~10 tests each) is a housekeeping follow-up.

## Verification at the end of all three PRs

```bash
python -m scripts.run_sp_cli &
sleep 2

echo "=== Routes mounted ==="
curl -s http://localhost:8080/openapi.json | jq '.paths | keys' | grep -E '/(linux|docker|elastic|catalog)/' | wc -l
# Expected: 13 (5 linux + 5 docker + 5 elastic + 2 catalog) — note elastic has 5 lifecycle paths

echo "=== Catalog reports 5 types, 3 available ==="
curl -s http://localhost:8080/catalog/types | jq '.entries | map(select(.available)) | length'
# Expected: 3

echo "=== Cross-section list works ==="
curl -s http://localhost:8080/catalog/stacks | jq '.stacks | length'
# Expected: 0 (no stacks running yet) — but the call succeeds

echo "=== Existing endpoints unchanged ==="
curl -s http://localhost:8080/openapi.json | jq '.paths["/ec2/playwright/list"]'
# Expected: not null
```

If all four checks pass, the backend is ready for the UI to bind to.
