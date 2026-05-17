# cli — EC2 FastAPI + Lambda Deploy

**Parent:** [`index.md`](index.md) | **Last updated:** 2026-05-17
**Source:** `_archive/v0.1.31/07__sp-cli-ec2-fastapi.md` + `08__sp-cli-lambda-deploy.md`.

The EC2 routes mounted on the stand-alone `Fast_API__SP__CLI` app, plus the deploy machinery that ships it as its own Lambda (`sp-playwright-cli-{stage}`) with its own IAM role, ECR repo, and Function URL.

---

## EXISTS (code-verified)

### Routes — action-mapped under `/ec2/playwright/...`

| Method | Path | Handler | Request → Response |
|--------|------|---------|--------------------|
| GET    | `/ec2/playwright/list`            | `Routes__Ec2__Playwright.list_instances`  | (no body) → `Schema__Ec2__Instance__List` |
| GET    | `/ec2/playwright/info/{name}`     | `Routes__Ec2__Playwright.info`            | path `{name}` (deploy-name or instance-id) → `Schema__Ec2__Instance__Info` (404 on miss) |
| POST   | `/ec2/playwright/create`          | `Routes__Ec2__Playwright.create`          | `Schema__Ec2__Create__Request` → `Schema__Ec2__Create__Response` |
| POST   | `/ec2/playwright/create/{name}`   | `Routes__Ec2__Playwright.create_named`    | path `{name}` + `Schema__Ec2__Create__Request` → `Schema__Ec2__Create__Response` |
| DELETE | `/ec2/playwright/delete/{name}`   | `Routes__Ec2__Playwright.delete`          | path `{name}` → `Schema__Ec2__Delete__Response` (404 on miss) |
| DELETE | `/ec2/playwright/delete-all`      | `Routes__Ec2__Playwright.delete_all`      | (no body) → `Schema__Ec2__Delete__Response` |

URL shape mirrors `sp <command> [<name>]` CLI: `/ec2/playwright/` is the resource group, `{command}` is the action, `{name}` is the instance handle (accepts deploy-name or instance-id via `Ec2__Service.resolve_target`).

Each method carries an explicit `__route_path__` so handler name and URL path are decoupled.

API-key middleware (`config.enable_api_key = True`) is on by default — requests need `X-API-Key` header matching `FAST_API__AUTH__API_KEY__VALUE`.

### Files

| File | Role |
|------|------|
| `ec2/primitives/Safe_Str__Deploy_Name.py`       | Adjective-noun deploy-name (MATCH regex) |
| `ec2/primitives/Safe_Str__Instance__Id.py`      | `i-[0-9a-f]{17}` |
| `ec2/primitives/Safe_Str__AMI__Id.py`           | `ami-[0-9a-f]{17}` |
| `ec2/primitives/Safe_Str__AWS__Account_Id.py`   | 12-digit AWS account id |
| `ec2/primitives/Safe_UInt__Max_Hours.py`        | Auto-delete window (0-168h) |
| `ec2/primitives/Safe_Str__Stage.py`             | Deployment stage id |
| `ec2/enums/Enum__Instance__State.py`            | EC2 lifecycle state |
| `ec2/schemas/Schema__Ec2__Preflight.py`         | account / region / registry / images / api-key-source |
| `ec2/schemas/Schema__Ec2__Create__Request.py`   | POST body |
| `ec2/schemas/Schema__Ec2__Create__Response.py`  | POST response; mirrors `sp create` output + embedded preflight |
| `ec2/schemas/Schema__Ec2__Instance__Info.py`    | GET response; mirrors `cmd_info` dict; carries `host_api_url` + `host_api_key_vault_path` (consumed by host-control) |
| `ec2/schemas/Schema__Ec2__Delete__Response.py`  | DELETE response; ids AWS accepted for termination |
| `ec2/collections/List__Instance__Id.py`         | `Type_Safe__List` for instance ids |
| `ec2/service/Ec2__Service.py`                   | Adapter over `scripts.provision_ec2.provision` / `find_instances` / `instance_terminate` |
| `fast_api/routes/Routes__Ec2__Playwright.py`    | Five endpoints (six after delete-all) |
| `fast_api/Fast_API__SP__CLI.py`                 | Stand-alone app; `config.enable_api_key = True`; `register_type_safe_handlers(self.app())` on `setup()` |
| `fast_api/lambda_handler.py`                    | Mangum wrapper for AWS Lambda |
| `fast_api/exception_handlers.py`                | `register_type_safe_handlers` — Type_Safe `ValueError` → HTTP 422 (post slice 9) |

### Tests

- `tests/unit/.../ec2/service/Ec2__Service__In_Memory.py` — real subclass; captures `last_create` + `last_deleted`.
- `tests/unit/.../fast_api/test_Fast_API__SP__CLI.py` — 10 TestClient cases: list / info-by-name / info-by-id / 404 / create (auto-name) / create-named (path overrides body) / delete / delete-404 / 422 on invalid `deploy_name` / 401 on missing API key.

### Type_Safe 422 handler

`Fast_API__SP__CLI.setup()` calls `register_type_safe_handlers(self.app())` which registers a FastAPI exception handler on `ValueError`. Response shape:

```json
{
  "detail": [{
    "type"      : "type_safe_value_error",
    "primitive" : "Safe_Str__Deploy_Name",
    "msg"       : "value does not match required pattern: ^[a-z]{3,20}-[a-z]{3,20}$"
  }],
  "hint": "Type-safe primitive rejected the request body..."
}
```

Parser regex `^in (Safe_[A-Za-z0-9_]+|Enum_[A-Za-z0-9_]+),\s*(.+)$`. Unknown shapes fall back to the original message — never empty.

---

### Lambda deployment — `sp-playwright-cli`

#### Why standalone

- **Security boundary** — the main Playwright service does not need `ec2:RunInstances` or `iam:PassRole`. Keeping those powers on a separate role shrinks blast radius.
- **Scaling / billing / monitoring** independent from the browser service.
- Matches the v0.1.72 brief — GH Actions hits this API on a schedule.

#### IAM role: `sp-playwright-cli-lambda`

Trust policy: only `lambda.amazonaws.com` can assume. All five `sp-cli-*` policies are **INLINE** (attached via `put_role_policy`).

| Inline policy | Scope |
|---------------|-------|
| `AWSLambdaBasicExecutionRole` (managed, attached by ARN) | CloudWatch logs |
| `sp-cli-ec2-management` | `ec2:RunInstances / TerminateInstances / Describe* / CreateSecurityGroup / AuthorizeSecurityGroup* / CreateTags` on `Resource: *` |
| `sp-cli-iam-passrole` | `iam:PassRole` ARN-scoped to `arn:aws:iam::{account}:role/playwright-ec2`, condition `iam:PassedToService = ec2.amazonaws.com`. Plus `iam:Get/CreateInstanceProfile / AddRoleToInstanceProfile`. Never `*`. |
| `sp-cli-ecr-read` | Pull-only: `GetAuthorizationToken / BatchGetImage / DescribeImages`. No push. |
| `sp-cli-sts-helpers` | `sts:GetCallerIdentity`, `sts:DecodeAuthorizationMessage` |
| `sp-cli-observability` | READ + DELETE only on AMP / OpenSearch / Grafana. No create or update. |

#### Image: `sp-playwright-cli`

- **Base:** `public.ecr.aws/lambda/python:3.12` — no Chromium.
- **Handler:** `sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler` (Mangum).
- **Build context:** repo root. `.dockerignore` keeps only `sgraph_ai_service_playwright__cli/` + `scripts/`.

#### Lambda: `sp-playwright-cli-{stage}`

| Setting | Value | Rationale |
|---------|-------|-----------|
| Memory  | 1024 MB | Adapter Lambda — all heavy work is AWS API calls |
| Timeout | 120 s   | `sp create` is ~60 s, 2× buffer |
| Architecture | x86_64 | Base image tag |
| Function URL | AuthType=NONE | API-key middleware inside the app gates every route |

Env vars: `FAST_API__AUTH__API_KEY__NAME` (default `X-API-Key`), `FAST_API__AUTH__API_KEY__VALUE` (required), `AWS_DEFAULT_REGION`.

#### Files (under `sgraph_ai_service_playwright__cli/deploy/`)

| File | Role |
|------|------|
| `images/sp_cli/dockerfile` | Image definition |
| `images/sp_cli/requirements.txt` | Lambda runtime deps (no Playwright) |
| `images/sp_cli/.dockerignore` | Scopes build context |
| `SP__CLI__Lambda__Policy.py` | Type_Safe — returns IAM policy dicts |
| `SP__CLI__Lambda__Role.py` | Creates / updates IAM role via `osbot-aws.IAM_Role` |
| `Docker__SP__CLI.py` | Image paths + ECR build/push |
| `Lambda__SP__CLI.py` | Lambda upsert + Function URL (two-statement AuthType=NONE pattern) |
| `provision.py` | Orchestrator: role → image → Lambda; `python -m … --stage dev` |

#### Tests (18 new; 52 total at the introducing commit)

- `tests/unit/.../deploy/test_SP__CLI__Lambda__Policy.py` — 8 cases (each policy's shape, security-critical assertions: PassRole not `*`; ECR pull-only; trust policy Lambda-only).
- `tests/unit/.../deploy/test_Docker__SP__CLI.py` — 6 cases.
- `tests/unit/.../deploy/test_Lambda__SP__CLI.py` — 4 cases.

#### How to deploy

```
python -m sgraph_ai_service_playwright__cli.deploy.provision --stage dev
```

Idempotent — re-run rolls the image + refreshes env vars. Prints the Function URL on success.

#### CI workflow

`.github/workflows/ci__sp_cli.yml` — runs on push/PR to `sgraph_ai_service_playwright__cli/**`, `scripts/provision_ec2.py`, `scripts/observability.py`, the workflow itself, or the SP CLI unit tests. Stage resolution: `workflow_dispatch` input wins; else `main` → `prod`, any other branch → `dev`.

### Known gaps

1. **No live deploy-via-pytest verification** — all tests are unit-level. Follow-up numbered tests (`test_1__ensure_role`, …) would mirror `tests/deploy/`.
2. **`Ec2__Service` is an adapter, not a full Type_Safe port** — converts `scripts/provision_ec2.py` dict returns into Type_Safe schemas. Full port still pending.
3. **`public_ip` / `*_image_uri` use `Safe_Str__Text`** rather than narrower primitives. `Safe_Str__Id` would sanitise dots; tighten when a real need appears.

---

## See also

- Parent: [`index.md`](index.md)
- Sources: [`_archive/v0.1.31/07__sp-cli-ec2-fastapi.md`](../_archive/v0.1.31/07__sp-cli-ec2-fastapi.md), [`08__sp-cli-lambda-deploy.md`](../_archive/v0.1.31/08__sp-cli-lambda-deploy.md)
- Host-control consumes `host_api_url` from `Schema__Ec2__Instance__Info`: [`host-control/index.md`](../host-control/index.md)
