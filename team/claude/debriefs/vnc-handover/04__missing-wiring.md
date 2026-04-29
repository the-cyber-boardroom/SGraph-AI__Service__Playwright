# `sp vnc` — Wiring to `Fast_API__SP__CLI` (VNC-only scope)

**Goal of this doc:** the minimum diff that makes `POST /vnc/stack`, `GET /vnc/stacks`, etc. answer on the deployed FastAPI service.

(Out of scope here: wiring `sp os` and `sp prom` routes too — same pattern; left for a later session. See doc 06 for the broader picture.)

## Where things stand

`Fast_API__SP__CLI.setup_routes()` mounts six route classes today (Catalog, Docker, Ec2, Elastic, Linux, Observability). VNC routes built in v0.1.96 are NOT mounted, so live HTTP requests to `/vnc/*` 404.

The route classes themselves are tested + green in standalone mode (each test creates its own `Fast_API()` and calls `app.add_routes(...)`), so the integration point is the only thing missing.

## Files to touch — total: 2

1. `sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py`
2. `tests/unit/sgraph_ai_service_playwright__cli/fast_api/test_Fast_API__SP__CLI.py`

## The diff (VNC-only)

### 1. `Fast_API__SP__CLI.py` — 4 lines added in 4 places

```python
# new imports
from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Stack import Routes__Vnc__Stack
from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Flows import Routes__Vnc__Flows
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service              import Vnc__Service

class Fast_API__SP__CLI(Fast_API):
    catalog_service       : Stack__Catalog__Service
    docker_service        : Docker__Service
    ec2_service           : Ec2__Service
    elastic_service       : Elastic__Service
    linux_service         : Linux__Service
    observability_service : Observability__Service
    vnc_service           : Vnc__Service                           # NEW

    def setup(self):
        self.linux_service .setup()
        self.docker_service.setup()
        self.vnc_service   .setup()                                # NEW — lazy-wires aws_client + 7 other helpers
        result = super().setup()
        register_type_safe_handlers(self.app())
        return result

    def setup_routes(self):
        self.add_routes(Routes__Stack__Catalog  , service=self.catalog_service      )
        self.add_routes(Routes__Docker__Stack   , service=self.docker_service       )
        self.add_routes(Routes__Ec2__Playwright , service=self.ec2_service          )
        self.add_routes(Routes__Elastic__Stack  , service=self.elastic_service      )
        self.add_routes(Routes__Linux__Stack    , service=self.linux_service        )
        self.add_routes(Routes__Observability   , service=self.observability_service)
        self.add_routes(Routes__Vnc__Stack      , service=self.vnc_service          )    # NEW
        self.add_routes(Routes__Vnc__Flows      , service=self.vnc_service          )    # NEW — same service, separate route file
```

### 2. `test_Fast_API__SP__CLI.py`

The existing test asserts a set of route paths. Add the 6 VNC paths:

```
POST   /vnc/stack
GET    /vnc/stacks
GET    /vnc/stack/{name}
DELETE /vnc/stack/{name}
GET    /vnc/stack/{name}/health
GET    /vnc/stack/{name}/flows
```

Open the test file and read its existing assertion block — add the six entries to whatever set/list it iterates. Each will resolve via `Routes__Vnc__Stack` (5 endpoints) and `Routes__Vnc__Flows` (1 endpoint).

## Important: `vnc_service.setup()` must be explicit

`Vnc__Service` has 8 lazy-init slots (`aws_client`, `probe`, `mapper`, `ip_detector`, `name_gen`, `compose_template`, `user_data_builder`, `interceptor_resolver`). Without the `.setup()` call, the first request hits `AttributeError: 'NoneType' object has no attribute 'instance'`. Same pitfall caught with `linux_service` in v0.1.101 — see `team/claude/debriefs/2026-04-29__v0.1.101__mvp-admin-user-ui.md` for the precedent.

## Sanity check after the change

```python
from sgraph_ai_service_playwright__cli.fast_api.Fast_API__SP__CLI import Fast_API__SP__CLI

app = Fast_API__SP__CLI().setup()
paths = sorted({r.path for r in app.app().routes})
assert '/vnc/stack'                       in paths
assert '/vnc/stacks'                      in paths
assert '/vnc/stack/{name}'                in paths
assert '/vnc/stack/{name}/health'         in paths
assert '/vnc/stack/{name}/flows'          in paths
```

If `vnc_service.setup()` is missing, the route registrations still pass at startup — the failure only surfaces on the first real request. The unit test in `tests/unit/.../fast_api/routes/test_Routes__Vnc__Stack.py` currently calls `service.list_stacks(...)` against a `_Fake_Service`, so it doesn't catch missing `.setup()`. **Add at least one route test that hits the real `Vnc__Service.setup()` chain** — eg. `assert isinstance(app.vnc_service.aws_client.sg, Vnc__SG__Helper)` after `app.setup()`.

## What NOT to do in this slice

- **Don't touch `Stack__Catalog__Service`** — see [05__catalog-integration.md](./05__catalog-integration.md). Catalog `entry__vnc()` already exists, so `GET /catalog/types` will list VNC. The catalog's `list_all_stacks(type='vnc')` will still return empty until the catalog service composes `vnc_service` — but that's a separate integration and not needed for the `/vnc/*` HTTP surface to work.
- **Don't add `OpenSearch__Service` / `Prometheus__Service` to `Fast_API__SP__CLI` in the same commit.** Same shape, but each adds its own ~3 LoC + tests. Keep the diff focused on VNC so the review stays small.

## Estimate

| Task | LoC | Time |
|---|---|---|
| `Fast_API__SP__CLI.py` edits | +4 lines | 5 min |
| Test additions | +6 paths in the existing assertion + 1 new `setup()` chain test | 10 min |
| Local sanity (run `pytest tests/unit/.../fast_api/`, hit `/vnc/stacks` via curl on a local uvicorn) | — | 10 min |

About 25 min of work. Single commit.
