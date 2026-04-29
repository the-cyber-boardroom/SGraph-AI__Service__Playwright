# Phase B · Step 6g — `sp prom` FastAPI routes (Tier-2B)

**Date:** 2026-04-28.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__05__sp-prom__prometheus.md`.
**Template:** Phase B step 5h (`aef4018`) — `sp os` FastAPI routes.
**Predecessor:** Phase B step 6f — `sp prom` create_stack wired (`c0911f7`).

---

## What shipped

5 FastAPI routes mirroring `Routes__OpenSearch__Stack`, each handler ~5 lines (zero logic — `service.method().json()`).

| File | Role |
|---|---|
| `prometheus/fast_api/routes/Routes__Prometheus__Stack.py` | 5 routes under `/prometheus`: `POST /stack`, `GET /stacks`, `GET/DELETE /stack/{name}` (404 on miss), `GET /stack/{name}/health`. |

## Departure from the `sp os` template — the create body

`Routes__OpenSearch__Stack.create(self, body: Schema__OS__Stack__Create__Request)` works because the OS Create request only contains primitives. The Prom Create request includes `scrape_targets : List__Schema__Prom__Scrape__Target` — a Type_Safe collection of nested Type_Safe schemas. FastAPI's pydantic-based body parser fails at route registration with:

```
PydanticSchemaGenerationError: Unable to generate pydantic-core schema for
List__Schema__Prom__Scrape__Target.
```

**Fix:** signature `body: dict` and explicit round-trip:

```python
def create(self, body: dict) -> dict:
    request = Schema__Prom__Stack__Create__Request.from_json(body)
    return self.service.create_stack(request).json()
```

This costs a slightly weaker OpenAPI spec for the create endpoint (body shows as a free-form dict in the schema), but preserves all behaviour and validation. The Type_Safe schema's regex / collection rules still fire at `from_json` time. A future cleanup could wire a custom `__get_pydantic_core_schema__` on the collection to restore strong typing in the spec.

## Tests

9 new tests, all green. Same `_Fake_Service(Prometheus__Service)` real-subclass pattern as the OS routes — no mocks; FastAPI TestClient drives the endpoints.

| Group | Tests |
|---|---|
| `list` | 2 — non-empty + empty |
| `info` | 2 — hit returns body, miss returns 404 with `'no prometheus stack'` |
| `create` | 2 — minimal body resolves defaults, pinned stack_name passes through |
| `delete` | 2 — hit returns terminated ids, miss returns 404 |
| `health` | 1 — query-string creds forward to `service.health(...)` and `targets_total` / `targets_up` flow back |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/prometheus/` | 152 | 161 | +9 |

## Bug surfaced + fixed

- `PydanticSchemaGenerationError` on `List__Schema__Prom__Scrape__Target` at route-add time. **Good failure** — caught at route-registration time, before any test could run. Fixed by `body: dict` + `from_json`. Same approach is the right escape hatch any time a future sister section's request schema includes a nested Type_Safe collection.

## Files changed

```
A  sgraph_ai_service_playwright__cli/prometheus/fast_api/__init__.py
A  sgraph_ai_service_playwright__cli/prometheus/fast_api/routes/__init__.py
A  sgraph_ai_service_playwright__cli/prometheus/fast_api/routes/Routes__Prometheus__Stack.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/fast_api/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/fast_api/routes/__init__.py
A  tests/unit/sgraph_ai_service_playwright__cli/prometheus/fast_api/routes/test_Routes__Prometheus__Stack.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 6h — `scripts/prometheus.py` typer app + Renderers, mounted on the main `sp` app via `add_typer` with `sp prom` short alias.
