# Reality — SP CLI Observability Routes

**Status:** live in code — Fast_API__SP__CLI now mounts both `Routes__Ec2`
and `Routes__Observability` on the same Lambda. 62/62 unit tests green.

The observability refactor landed in slices 1 + 2 (commits `56dd7c7` +
`bf19f9a`) as pure Type_Safe logic; this slice wires it onto HTTP so GH
Actions can drive the morning create + evening delete workflow straight
from the brief (v0.1.72).

---

## New routes on `Fast_API__SP__CLI`

| Method | Path                              | Handler | Returns |
|--------|-----------------------------------|---------|---------|
| GET    | `/observability/stacks`           | `Routes__Observability.stacks`       | `Schema__Stack__List` (envelope with `region` + `stacks[]`) |
| GET    | `/observability/stacks/{name}`    | `Routes__Observability.get_stack`    | `Schema__Stack__Info` (404 when all three components absent) |
| DELETE | `/observability/stacks/{name}`    | `Routes__Observability.delete_stack` | `Schema__Stack__Delete__Response` (one per-component result — never 404; "already gone" is semantic data, not an error) |

Same `Fast_API__Routes` / `__route_path__` pattern as `Routes__Ec2`.
GET + DELETE share `/stacks/{name}`, disambiguated by HTTP verb.

## `Fast_API__SP__CLI` changes

- New field `observability_service : Observability__Service` (Type_Safe auto-initialises).
- `setup_routes()` mounts `Routes__Observability` with the injected service.

## New files

| File | Role |
|------|------|
| `sgraph_ai_service_playwright__cli/fast_api/routes/Routes__Observability.py`        | Three HTTP endpoints, pure delegation |
| `sgraph_ai_service_playwright__cli/fast_api/exception_handlers.py`                   | Bridges Type_Safe `ValueError` → HTTP 422 (see Task A below) |
| `tests/unit/.../fast_api/test_Routes__Observability.py`                              | 5 TestClient cases — list, populated info, 404, DELETE aggregate, auth |
| `tests/unit/.../fast_api/test_exception_handlers.py`                                 | 5 cases — message parser, unknown shapes, empty-safe |

## Task A side-effect: Type_Safe ValueError → HTTP 422

Previously documented as a known gap in slice 3. Now closed.

`Fast_API__SP__CLI.setup()` calls `register_type_safe_handlers(self.app())`
which registers a FastAPI exception handler on `ValueError`. Applies to
every route on the app (EC2 + Observability + any future mount). Response:

```json
{
  "detail": [{
    "type"      : "type_safe_value_error",
    "primitive" : "Safe_Str__Deploy_Name",
    "msg"       : "value does not match required pattern: ^[a-z]{3,20}-[a-z]{3,20}$"
  }],
  "hint": "Type-safe primitive rejected the request body. Review the `primitive` field..."
}
```

Parser regex `^in (Safe_[A-Za-z0-9_]+|Enum_[A-Za-z0-9_]+),\s*(.+)$` extracts
the primitive class name from the message Safe_* classes raise. Unknown
shapes (e.g. non-primitive ValueError from user code) fall back to the
original message text — the response is never empty.

## Deployment implication

Nothing changes on the Lambda deploy side — the new routes live in the
same `Fast_API__SP__CLI` app, baked into the same image, served by the
same Function URL. The CI pipeline (`.github/workflows/ci__sp_cli.yml`)
picks these up automatically on the next push that matches its path
filters.

## What closes from the brief (v0.1.72)

| Brief-promised surface | Status |
|------------------------|--------|
| `POST /v1/observability/stack`       (create)           | **Still PROPOSED** — mutation path not yet written. |
| `DELETE /v1/observability/stack/{name}`                 | **Delivered** (minus the `/v1/` prefix — apply at API-GW / Function URL proxy if needed) |
| `GET /v1/observability/stacks`                          | **Delivered** |
| `GET /v1/observability/stack/{name}`                    | **Delivered** (via `get_stack`) |
| `POST /v1/observability/stack/{name}/backup`            | **Still PROPOSED** |
| `POST /v1/observability/stack/{name}/restore`           | **Still PROPOSED** |
| `POST /v1/observability/stack/{name}/dashboard-import`  | **Still PROPOSED** |

## Known gaps

1. **Path prefix `/v1/` not applied** — the brief uses `/v1/observability/...`.
   The Lambda mounts at `/observability/...`. Add `/v1/` via API-GW stage
   path, or prepend the tag here with a dedicated `prefix` attribute on
   the `Fast_API__Routes` subclass. Not urgent — the Function URL can
   rewrite.
2. **Mutation ops for observability (create/backup/restore/dashboard-import)**
   are still scripts-only. Follow-up slices will add them following the
   same Type_Safe / adapter pattern used for delete.
