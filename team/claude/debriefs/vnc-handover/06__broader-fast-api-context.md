# Appendix — wiring `sp os` and `sp prom` later

This is **not part of the current VNC-only slice.** Captured here so the next agent doesn't lose the context.

The same gap that exists for VNC also exists for `sp os` (`Routes__OpenSearch__Stack`) and `sp prom` (`Routes__Prometheus__Stack`). Both have full route classes + tests, neither is mounted on `Fast_API__SP__CLI`.

## Same pattern, three sections

When the time comes to wire OS + Prom, copy the VNC change in [`04__missing-wiring.md`](./04__missing-wiring.md) and apply it twice more:

```python
# Add 6 more imports (3 services + 3 route files; OS and Prom each have one route file)
from sgraph_ai_service_playwright__cli.opensearch.fast_api.routes.Routes__OpenSearch__Stack import Routes__OpenSearch__Stack
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Service              import OpenSearch__Service
from sgraph_ai_service_playwright__cli.prometheus.fast_api.routes.Routes__Prometheus__Stack import Routes__Prometheus__Stack
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Service              import Prometheus__Service

# Add 2 fields
opensearch_service : OpenSearch__Service
prometheus_service : Prometheus__Service

# Add 2 setup() calls
self.opensearch_service.setup()
self.prometheus_service.setup()

# Add 2 add_routes() calls
self.add_routes(Routes__OpenSearch__Stack , service=self.opensearch_service )
self.add_routes(Routes__Prometheus__Stack , service=self.prometheus_service )
```

Each is its own commit (one for OS, one for Prom) so PRs stay small.

## Endpoints unlocked

```
# sp os (5 endpoints)
POST   /opensearch/stack
GET    /opensearch/stacks
GET    /opensearch/stack/{name}
DELETE /opensearch/stack/{name}
GET    /opensearch/stack/{name}/health

# sp prom (5 endpoints)
POST   /prometheus/stack
GET    /prometheus/stacks
GET    /prometheus/stack/{name}
DELETE /prometheus/stack/{name}
GET    /prometheus/stack/{name}/health
```

## Catalog integration (deferred)

After all three are wired, `Stack__Catalog__Service.list_all_stacks` still won't enumerate them — see [`05__catalog-integration.md`](./05__catalog-integration.md). That's a separate slice with its own test fan-out.
