# `sp vnc` — Tier-2B (FastAPI)

The HTTP surface. Built and tested via FastAPI TestClient, but **NOT YET WIRED** to the main `Fast_API__SP__CLI` app — see [04__missing-wiring.md](./04__missing-wiring.md).

## Route files

`cli/vnc/fast_api/routes/`:

| File | Endpoints |
|---|---|
| `Routes__Vnc__Stack.py` | 5 stack-lifecycle routes |
| `Routes__Vnc__Flows.py` | 1 flows-listing route |

## Endpoints

```
POST   /vnc/stack                       — create   (body: dict — see note below)
GET    /vnc/stacks                      — list     [?region=…]
GET    /vnc/stack/{name}                — info     [?region=…]                          (404 on miss)
DELETE /vnc/stack/{name}                — delete   [?region=…]                          (404 on miss)
GET    /vnc/stack/{name}/health         — health   [?region=…&username=…&password=…]
GET    /vnc/stack/{name}/flows          — flows    [?region=…&username=…&password=…]
```

Tag prefix `/vnc` — OpenAPI groups all 6 endpoints together.

## The `body: dict` workaround on `create`

`Routes__Vnc__Stack.create` takes `body: dict` and round-trips through `Schema__Vnc__Stack__Create__Request.from_json(body)` rather than typing the parameter as the schema directly:

```python
def create(self, body: dict) -> dict:
    request = Schema__Vnc__Stack__Create__Request.from_json(body)
    return self.service.create_stack(request).json()
```

**Why:** the request schema carries a nested `Schema__Vnc__Interceptor__Choice` (a Type_Safe with its own enum + nested fields). FastAPI's pydantic-based body parser fails at route registration with `PydanticSchemaGenerationError` for nested Type_Safe collections.

`Routes__Prometheus__Stack.create` uses the same workaround (Prom's request carries `List__Schema__Prom__Scrape__Target`).

The Type_Safe schema's regex / collection rules still fire at `from_json` time, so validation isn't lost — just the OpenAPI spec shows `body: dict` instead of the structured shape.

## Flows endpoint shape

`Routes__Vnc__Flows.flows` returns:

```json
{"flows": [
  {"flow_id": "abc123", "method": "GET",  "url": "https://example.com/x", "status_code": 200, "intercepted_at": "2026-04-29T10:00:00Z"},
  {"flow_id": "def456", "method": "POST", "url": "https://example.com/y", "status_code": 0,   "intercepted_at": ""}
]}
```

Envelope shape (not bare list) so future fields (total / dropped / cursor) can be added without breaking clients. Per N4 there's no auto-export — flows live on the EC2 and die with it; this is just a peek.

## Tests

`tests/unit/sgraph_ai_service_playwright__cli/vnc/fast_api/routes/`:
- `test_Routes__Vnc__Stack.py` — 9 tests via FastAPI TestClient
- `test_Routes__Vnc__Flows.py` — 4 tests

Pattern: real `_Fake_Service(Vnc__Service)` subclass that overrides only the 6 service methods. No `unittest.mock`.

```python
class _Fake_Service(Vnc__Service):
    def list_stacks(self, region):  ...                 # scripted return
    def create_stack(self, request, creator=''): ...    # captures `request` into self.last_create_req
    # etc.

def _client(service):
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Vnc__Stack, service=service)
    return app.client()
```

This is the same shape used by `Routes__OpenSearch__Stack` / `Routes__Prometheus__Stack` tests — copy from there for any new sister-section route tests.

## Why this is "not wired" but still tested

The route classes work end-to-end in their own test setup (each test creates its own `Fast_API()` app and adds the routes). The integration with the main `Fast_API__SP__CLI` is a separate step — see doc 04.
