# Reality — SP CLI EC2 FastAPI Routes — Slice 3

**Status:** partial — create/info/delete for EC2 instances exposed as HTTP
routes in a **stand-alone** FastAPI app (`Fast_API__SP__CLI`). The existing
`Fast_API__Playwright__Service` is not modified. `scripts/provision_ec2.py`
is not modified — the new service adapts its existing functions.

---

## New routes

| Method | Path | Handler | Request → Response |
|--------|------|---------|--------------------|
| POST   | `/ec2/instances`          | `Routes__Ec2.instances`       | `Schema__Ec2__Create__Request` → `Schema__Ec2__Create__Response` |
| GET    | `/ec2/instances/{target}` | `Routes__Ec2.get_instance`    | path param `target` (deploy-name or instance-id) → `Schema__Ec2__Instance__Info` (404 when no match) |
| DELETE | `/ec2/instances/{target}` | `Routes__Ec2.delete_instance` | path param `target` → `Schema__Ec2__Delete__Response` (404 when no match) |

`Routes__Ec2.delete_instance` and `Routes__Ec2.get_instance` share the same
URL; the osbot-fast-api path parser normally derives the path from the
method name, so both methods carry an explicit `__route_path__` attribute
to let them co-exist on `/instances/{target}` under different verbs.

API-key middleware (`config.enable_api_key = True`) is on by default —
requests need an `X-API-Key` header matching `FAST_API__AUTH__API_KEY__VALUE`.

## Deployment

- `sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py` —
  stand-alone app; extends `osbot_fast_api.api.Fast_API`. Run under
  uvicorn, Docker, or any ASGI host.
- `sgraph_ai_service_playwright__cli/fast_api/lambda_handler.py` — Mangum
  wrapper for AWS Lambda. Handler path:
  `sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler`.

## New files

### `sgraph_ai_service_playwright__cli/ec2/`

| File | Role |
|------|------|
| `primitives/Safe_Str__Deploy_Name.py`       | adjective-noun deploy-name (MATCH regex) |
| `primitives/Safe_Str__Instance__Id.py`      | `i-[0-9a-f]{17}` |
| `primitives/Safe_Str__AMI__Id.py`           | `ami-[0-9a-f]{17}` |
| `primitives/Safe_Str__AWS__Account_Id.py`   | 12-digit AWS account id |
| `primitives/Safe_UInt__Max_Hours.py`        | Auto-delete window (0-168h) |
| `primitives/Safe_Str__Stage.py`             | Deployment stage id |
| `enums/Enum__Instance__State.py`            | EC2 lifecycle state (AWS vocabulary + UNKNOWN) |
| `schemas/Schema__Ec2__Preflight.py`         | account / region / registry / images / api-key-source |
| `schemas/Schema__Ec2__Create__Request.py`   | POST body |
| `schemas/Schema__Ec2__Create__Response.py`  | POST response; mirrors `sp create` output shape + embedded preflight |
| `schemas/Schema__Ec2__Instance__Info.py`    | GET response; mirrors `cmd_info` dict |
| `schemas/Schema__Ec2__Delete__Response.py`  | DELETE response; ids AWS accepted for termination |
| `collections/List__Instance__Id.py`         | `Type_Safe__List` for instance ids |
| `service/Ec2__Service.py`                   | Adapter over `scripts.provision_ec2.provision` / `find_instances` / `instance_terminate` |

### `sgraph_ai_service_playwright__cli/fast_api/`

| File | Role |
|------|------|
| `routes/Routes__Ec2.py`                     | `Fast_API__Routes` subclass; three endpoints |
| `Fast_API__SP__CLI.py`                      | Stand-alone app; `config.enable_api_key = True` |
| `lambda_handler.py`                         | Mangum wrapper for AWS Lambda deploys |

## Tests (34 passing across the whole new package; 8 new here)

| File | Coverage |
|------|----------|
| `tests/unit/.../ec2/service/Ec2__Service__In_Memory.py`     | Real subclass (no mocks); captures `last_create` + `last_deleted` for assertions |
| `tests/unit/.../fast_api/test_Fast_API__SP__CLI.py`         | 8 TestClient cases — POST/GET/DELETE happy paths, 404 on missing target, 401 on missing API key, invalid input → ≥400 |

## Design notes

- **No sync/async concerns**: user says `sp create` completes in <1 min, well below Lambda's 15-min cap and API Gateway's 29-s default (bump to 29s if deploying behind API GW — Function URLs have no such cap).
- **`preflight_check` has `sys.exit(1)`** on credential failure — fatal for any FastAPI route. The adapter replicates only the pure-data half of preflight inline (aws_account / aws_region / ecr_registry_host / default image URIs / api-key generation) so route handlers can catch failures as exceptions rather than process exits.
- **`_resolve_target` in scripts uses `typer.prompt`** for disambiguation. The adapter requires a concrete `target` — no prompting, no auto-select — so ambiguous requests return 404 rather than hanging.

## Known tech debt (flagged in commit + headers)

1. **`Ec2__Service` is an adapter, not a full Type_Safe port** — it imports and calls `scripts.provision_ec2` functions and converts their dict returns into Type_Safe schemas. When the full port of `provision_ec2.py` (2847 lines) lands, only the method bodies here need to change; the schemas/routes/tests stay.
2. **Type_Safe primitive validation errors become HTTP 500, not 422** — osbot-fast-api's `Type_Safe__Route__Converter` raises `ValueError` on invalid input; FastAPI's default handler maps that to 500. `test_post_instances__rejects_invalid_deploy_name` documents the current behaviour with `raise_server_exceptions=False`. Follow-up: wire a framework-level handler (or override the converter) to produce 422 + a body that lists the offending fields.
3. **`public_ip` / `*_image_uri` use `Safe_Str__Text`** rather than narrower primitives (`Safe_Str__IP_Address`, bespoke `Safe_Str__ECR__Image_Uri`). `Safe_Str__Id` would sanitise dots to underscores — wrong for these shapes. Text is permissive but correct; tighten when a real validation need appears.
