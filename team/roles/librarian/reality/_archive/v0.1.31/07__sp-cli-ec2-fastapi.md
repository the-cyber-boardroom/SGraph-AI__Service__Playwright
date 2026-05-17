# Reality — SP CLI EC2 FastAPI Routes — Slice 3

**Status:** partial — list/info/create/delete for EC2 instances exposed as
HTTP routes in a **stand-alone** FastAPI app (`Fast_API__SP__CLI`). The
existing `Fast_API__Playwright__Service` is not modified.
`scripts/provision_ec2.py` is not modified — the new service adapts its
existing functions.

---

## Routes — action-mapped under `/ec2/playwright/...`

| Method | Path                                | Handler                                    | Request → Response |
|--------|-------------------------------------|--------------------------------------------|--------------------|
| GET    | `/ec2/playwright/list`              | `Routes__Ec2__Playwright.list_instances`   | (no body) → `Schema__Ec2__Instance__List` |
| GET    | `/ec2/playwright/info/{name}`       | `Routes__Ec2__Playwright.info`             | path `{name}` (deploy-name or instance-id) → `Schema__Ec2__Instance__Info` (404 on miss) |
| POST   | `/ec2/playwright/create`            | `Routes__Ec2__Playwright.create`           | `Schema__Ec2__Create__Request` → `Schema__Ec2__Create__Response` (deploy_name from body or auto-generated) |
| POST   | `/ec2/playwright/create/{name}`     | `Routes__Ec2__Playwright.create_named`     | path `{name}` + `Schema__Ec2__Create__Request` → `Schema__Ec2__Create__Response` (path overrides body's `deploy_name`) |
| DELETE | `/ec2/playwright/delete/{name}`     | `Routes__Ec2__Playwright.delete`           | path `{name}` → `Schema__Ec2__Delete__Response` (404 on miss) |

The URL shape mirrors the `sp <command> [<name>]` CLI: `/ec2/playwright/`
is the resource group (Playwright EC2 stack: Playwright service +
agent_mitmproxy sidecar + headless Chromium), `{command}` is the action,
`{name}` is the instance handle. `name` accepts either the deploy-name or
the instance-id — `Ec2__Service.resolve_target` handles both.

Each method carries an explicit `__route_path__` so the handler name and
the URL path are decoupled (the parser would otherwise derive paths from
the method name, which can't express `/info/{name}` cleanly).

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
| `routes/Routes__Ec2__Playwright.py`         | `Fast_API__Routes` subclass; five endpoints under `/ec2/playwright/` (list / info / create / create-named / delete) |
| `Fast_API__SP__CLI.py`                      | Stand-alone app; `config.enable_api_key = True` |
| `lambda_handler.py`                         | Mangum wrapper for AWS Lambda deploys |

## Tests (34 passing across the whole new package; 8 new here)

| File | Coverage |
|------|----------|
| `tests/unit/.../ec2/service/Ec2__Service__In_Memory.py`     | Real subclass (no mocks); captures `last_create` + `last_deleted` for assertions |
| `tests/unit/.../fast_api/test_Fast_API__SP__CLI.py`         | 10 TestClient cases — list / info-by-name / info-by-id / 404 / create (auto-name) / create-named (path overrides body) / delete / delete-404 / 422 on invalid `deploy_name` / 401 on missing API key |

## Design notes

- **No sync/async concerns**: user says `sp create` completes in <1 min, well below Lambda's 15-min cap and API Gateway's 29-s default (bump to 29s if deploying behind API GW — Function URLs have no such cap).
- **`preflight_check` has `sys.exit(1)`** on credential failure — fatal for any FastAPI route. The adapter replicates only the pure-data half of preflight inline (aws_account / aws_region / ecr_registry_host / default image URIs / api-key generation) so route handlers can catch failures as exceptions rather than process exits.
- **`_resolve_target` in scripts uses `typer.prompt`** for disambiguation. The adapter requires a concrete `target` — no prompting, no auto-select — so ambiguous requests return 404 rather than hanging.

## Known tech debt (flagged in commit + headers)

1. **`Ec2__Service` is an adapter, not a full Type_Safe port** — it imports and calls `scripts.provision_ec2` functions and converts their dict returns into Type_Safe schemas. When the full port of `provision_ec2.py` (2847 lines) lands, only the method bodies here need to change; the schemas/routes/tests stay.
2. ~~Type_Safe primitive validation errors become HTTP 500, not 422~~ — **RESOLVED.** `Fast_API__SP__CLI.setup()` now calls `register_type_safe_handlers(self.app())` which registers a FastAPI exception handler on `ValueError`. The handler parses the "in <Primitive>, <msg>" shape used by every Safe_* primitive and returns HTTP 422 with a structured body: `{'detail': [{'type': 'type_safe_value_error', 'primitive': '<class>', 'msg': '<reason>'}], 'hint': ...}`. Unknown-shape ValueErrors still surface as 422 with the original message so the response is never empty.
3. **`public_ip` / `*_image_uri` use `Safe_Str__Text`** rather than narrower primitives (`Safe_Str__IP_Address`, bespoke `Safe_Str__ECR__Image_Uri`). `Safe_Str__Id` would sanitise dots to underscores — wrong for these shapes. Text is permissive but correct; tighten when a real validation need appears.
