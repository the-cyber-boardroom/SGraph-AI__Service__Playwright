# cli — Observability + Linux/Docker/Elastic/Catalog/VNC Routes

**Parent:** [`index.md`](index.md) | **Last updated:** 2026-05-17
**Source:** `_archive/v0.1.31/09__sp-cli-observability-routes.md` + `13__sp-cli-linux-docker-elastic-catalog-ui.md` (route mounts).

> **Scope note (v0.2.29):** This file covers the AMP/OpenSearch/AMG **infrastructure** surface (`Observability__AWS__Client` / `Observability__Service` — manages monitoring workspaces). The unified observability **read** surface (`sg aws observe` REPL — tail, query, stats, agent-trace across S3/CloudWatch/CloudTrail) is a separate package under `aws/observe/` and will be documented at [`aws-observe.md`](aws-observe.md) once Slice H lands. The two are complementary, not competing.

The Tier-1 observability service and its routes (`/observability/*`), plus the slice-13 / slice-14 mounts that bring `Routes__Linux__Stack`, `Routes__Docker__Stack`, `Routes__Stack__Catalog`, `Routes__Elastic__Stack`, `Routes__Vnc__Stack`, `Routes__Vnc__Flows` onto `Fast_API__SP__CLI`.

---

## EXISTS (code-verified)

### `observability/` — Tier-1 pure-logic service

| File | Role |
|------|------|
| `primitives/Safe_Str__Stack__Name.py` | AWS OS-domain-name compliant (3-28 chars, lowercase, starts with letter) |
| `primitives/Safe_Str__AWS__Region.py` | Region code (MATCH regex). Empty allowed = resolve at runtime |
| `primitives/Safe_Str__AWS__Endpoint.py` | Service endpoint hostname (no scheme) |
| `primitives/Safe_Int__Document__Count.py` | OS doc count; `-1` sentinel = not queried |
| `enums/Enum__Stack__Component__Status.py` | Normalised lifecycle state across AMP/OS/AMG |
| `enums/Enum__Stack__Component__Kind.py` | Identifies AWS service per component |
| `enums/Enum__Component__Delete__Outcome.py` | `DELETED / NOT_FOUND / FAILED` |
| `schemas/Schema__Stack__Component__AMP.py` | AMP workspace view |
| `schemas/Schema__Stack__Component__OpenSearch.py` | OpenSearch domain view |
| `schemas/Schema__Stack__Component__Grafana.py` | AMG workspace view |
| `schemas/Schema__Stack__Info.py` | Aggregate view (AMP + OS + AMG; each nullable) |
| `schemas/Schema__Stack__List.py` | `list_stacks` envelope (carries region) |
| `schemas/Schema__Stack__Component__Delete__Result.py` | Per-component delete outcome |
| `schemas/Schema__Stack__Delete__Response.py` | `delete_stack` envelope |
| `collections/List__Stack__Info.py` | `Type_Safe__List` |
| `collections/List__Stack__Component__Delete__Result.py` | `Type_Safe__List` |
| `service/Observability__AWS__Client.py` | **Only file in this package that imports boto3.** Methods: `amp_workspaces`, `opensearch_domains`, `amg_workspaces`, `opensearch_document_count`, `amp_delete_workspace`, `opensearch_delete_domain`, `amg_delete_workspace` |
| `service/Observability__Service.py` | Pure logic: `list_stacks`, `get_stack_info`, `delete_stack`, `resolve_region` |

Tests: 26 passing, 0 skipped. Stack-name / region primitive tests; schema round-trips; `Observability__AWS__Client__In_Memory` (real subclass — no mocks); service list / get / delete / region-resolve cases.

---

### `Routes__Observability` — 3 routes mounted on `Fast_API__SP__CLI`

| Method | Path | Handler | Returns |
|--------|------|---------|---------|
| GET    | `/observability/stacks`           | `Routes__Observability.stacks`       | `Schema__Stack__List` |
| GET    | `/observability/stacks/{name}`    | `Routes__Observability.get_stack`    | `Schema__Stack__Info` (404 when all three components absent) |
| DELETE | `/observability/stacks/{name}`    | `Routes__Observability.delete_stack` | `Schema__Stack__Delete__Response` (one per-component result — never 404; "already gone" is semantic data, not an error) |

`Fast_API__SP__CLI` changes (slice 9):

- New field `observability_service : Observability__Service`.
- `setup_routes()` mounts `Routes__Observability` with the injected service.
- `setup()` calls `register_type_safe_handlers(self.app())` — bridges Type_Safe `ValueError` → HTTP 422 (closes the slice-3 gap, see [`ec2.md`](ec2.md)).

Tests: 5 TestClient cases in `tests/unit/.../fast_api/test_Routes__Observability.py` (list, populated info, 404, DELETE aggregate, auth). 5 cases in `test_exception_handlers.py`.

What closes from the v0.1.72 brief:

| Brief surface | Status |
|---------------|--------|
| `GET /v1/observability/stacks` | Delivered (no `/v1/` prefix; apply at API-GW if needed) |
| `GET /v1/observability/stack/{name}` | Delivered |
| `DELETE /v1/observability/stack/{name}` | Delivered |
| `POST /v1/observability/stack` (create) | Still PROPOSED |
| `POST /v1/observability/stack/{name}/backup` | Still PROPOSED |
| `POST /v1/observability/stack/{name}/restore` | Still PROPOSED |
| `POST /v1/observability/stack/{name}/dashboard-import` | Still PROPOSED |

---

### Slice 13 — Linux/Docker mounts + Catalog + Elastic routes

#### PR-1 — Linux + Docker routes mounted

Route classes existed; slice 13 wired them in.

| Method | Path | Handler |
|--------|------|---------|
| GET    | `/linux/stacks`              | `Routes__Linux__Stack.list_stacks`  |
| GET    | `/linux/stack/{name}`        | `Routes__Linux__Stack.info`         |
| POST   | `/linux/stack`               | `Routes__Linux__Stack.create`       |
| DELETE | `/linux/stack/{name}`        | `Routes__Linux__Stack.delete`       |
| GET    | `/linux/stack/{name}/health` | `Routes__Linux__Stack.health`       |
| GET    | `/docker/stacks`             | `Routes__Docker__Stack.list_stacks` |
| GET    | `/docker/stack/{name}`       | `Routes__Docker__Stack.info`        |
| POST   | `/docker/stack`              | `Routes__Docker__Stack.create`      |
| DELETE | `/docker/stack/{name}`       | `Routes__Docker__Stack.delete`      |
| GET    | `/docker/stack/{name}/health`| `Routes__Docker__Stack.health`      |

**Schema fix:** `extra_ports: List__Port` changed to `List[int]` in both `Schema__Linux__Create__Request` and `Schema__Docker__Create__Request` — `Type_Safe__List` subclasses are not handled by `Type_Safe__To__BaseModel`, so `List[int]` is required for FastAPI startup.

#### PR-2 — `catalog/` sub-package + `Routes__Stack__Catalog`

`sgraph_ai_service_playwright__cli/catalog/`:

- **Enums:** `Enum__Stack__Type` — `LINUX`, `DOCKER`, `ELASTIC`, `OPENSEARCH`, `VNC`.
- **Schemas:** `Schema__Stack__Type__Catalog__Entry` (per-type metadata), `Schema__Stack__Type__Catalog` (response for `/catalog/types`), `Schema__Stack__Summary` (type-agnostic running stack), `Schema__Stack__Summary__List` (response for `/catalog/stacks`).
- **Collections:** `List__Schema__Stack__Type__Catalog__Entry`, `List__Schema__Stack__Summary`.
- **Service:** `Stack__Catalog__Service__Entries` (mixin builds 5 entries); `Stack__Catalog__Service` (composes Linux/Docker/Elastic; `get_catalog()` + `list_all_stacks(type_filter)`).
- **Routes:** `Routes__Stack__Catalog` (tag `catalog`).

| Method | Path | Notes |
|--------|------|-------|
| GET | `/catalog/types`  | All 5 types; linux/docker/elastic `available=True`; opensearch/vnc `available=False` initially (vnc flipped to True in slice 14) |
| GET | `/catalog/stacks` | Cross-section list; optional `?type=linux\|docker\|elastic` filter; 422 on unknown type |

#### PR-3 — `Routes__Elastic__Stack`

`sgraph_ai_service_playwright__cli/elastic/fast_api/routes/`:

| Method | Path | Handler |
|--------|------|---------|
| GET    | `/elastic/stacks`              | `Routes__Elastic__Stack.list_stacks` |
| GET    | `/elastic/stack/{name}`        | `Routes__Elastic__Stack.info` (404 on miss) |
| POST   | `/elastic/stack`               | `Routes__Elastic__Stack.create` |
| DELETE | `/elastic/stack/{name}`        | `Routes__Elastic__Stack.delete` (404 on miss: empty `target` field) |
| GET    | `/elastic/stack/{name}/health` | `Routes__Elastic__Stack.health` |

Service signatures (verified against `Elastic__Service.py`):
- `create(body)` — not `create_stack`.
- `get_stack_info(stack_name, region)` — name-first.
- `delete_stack(stack_name, region)` — name-first.
- `health(stack_name, password, check_ssm)` — no `region` param.

---

### Slice 14 — VNC stack + flows mounts

`Fast_API__SP__CLI` gained `vnc_service: Vnc__Service` (with `setup()` call) and `Stack__Catalog__Service` gained `vnc_service` field + VNC branch in `list_all_stacks()`.

| Method | Path |
|--------|------|
| POST   | `/vnc/stack` |
| GET    | `/vnc/stacks` |
| GET    | `/vnc/stack/{name}` |
| DELETE | `/vnc/stack/{name}` |
| GET    | `/vnc/stack/{name}/health` |
| GET    | `/vnc/stack/{name}/flows` |

VNC bug fix: `Vnc__Service.list_stacks` got `region = region or DEFAULT_REGION` guard (was passing `''` to boto3, causing `https://ec2..amazonaws.com` invalid-endpoint 422).

New primitive: `catalog/primitives/Safe_Str__Endpoint__Path.py` — allows `/`, `-`, `_`, `{`, `}` (replaced `Safe_Str__Text` which converted `/` → `_`, breaking UI fetch URLs).

Schema changes:
- `Schema__Stack__Type__Catalog__Entry.*_endpoint_path` type changed from `Safe_Str__Text` → `Safe_Str__Endpoint__Path`.
- `Schema__Stack__Type__Catalog__Entry.default_max_hours` default changed from `4` → `1`.

---

### `Fast_API__SP__CLI` — total route surface

| Slice | Endpoints added | Total |
|-------|-----------------|-------|
| PR-0 (EC2 + observability) | 10 | 10 |
| Slice 13 PR-1 (linux+docker) | 10 | 20 |
| Slice 13 PR-2 (catalog) | 2 | 22 |
| Slice 13 PR-3 (elastic) | 5 | 27 |
| Slice 14 (vnc + flows) | 6 | **33** |

### Tests added

| Suite | New tests | Approach |
|-------|-----------|----------|
| `test_Fast_API__SP__CLI.py` | +4 mounting tests (linux, docker, catalog, elastic) + 2 for VNC | Path-set membership |
| `catalog/schemas/test_catalog_schemas.py` | Schema round-trips | Type_Safe `.json()` |
| `catalog/service/test_Stack__Catalog__Service.py` | 4 tests | `_Fake_*` real subclasses |
| `catalog/service/test_Stack__Catalog__Service__list.py` | 4 tests | same |
| `catalog/fast_api/routes/test_Routes__Stack__Catalog.py` | 5 tests | TestClient |
| `elastic/fast_api/routes/test_Routes__Elastic__Stack.py` | 5 list/info tests | TestClient + `_Fake_Elastic__Service` |
| `elastic/fast_api/routes/test_Routes__Elastic__Stack__write.py` | 5 create/delete/health tests | same |

Total suite at slice 13: **1176 passing**.

---

## Known gaps / tech debt

1. **boto3 in `Observability__AWS__Client`** — violates CLAUDE.md rule 8 (osbot-aws only). No osbot-aws wrapper for AMP / OpenSearch / Grafana yet; boundary isolated to one file with a header comment.
2. **`Safe_Str__Stack__Name` hash mismatch with plain-dict keys** — `Observability__Service.get_stack_info` casts to `str()`. Replace internal `Dict[str, …]` with a `Dict__*` collection subclass keyed by the Safe primitive.
3. **`/v1/` prefix not applied** — the v0.1.72 brief uses `/v1/observability/...`; Lambda mounts at `/observability/...`. Apply `/v1/` via API-GW stage or `prefix` attribute on `Fast_API__Routes`.

---

## See also

- Parent: [`index.md`](index.md)
- Sources: [`_archive/v0.1.31/09__sp-cli-observability-routes.md`](../_archive/v0.1.31/09__sp-cli-observability-routes.md), [`13__sp-cli-linux-docker-elastic-catalog-ui.md`](../_archive/v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md)
- UI consumers: [`ui/index.md`](../ui/index.md)
