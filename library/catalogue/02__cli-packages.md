# 02 — CLI Sub-Packages

→ [Catalogue README](README.md)

All code lives under `sgraph_ai_service_playwright__cli/`.
Each sub-package follows the same layered layout: `enums/`, `primitives/`, `schemas/`, `collections/`, `service/`.

---

## `aws/` — Shared AWS Naming

| File | Role |
|------|------|
| `aws/Stack__Naming.py` | Binds a `section_prefix`; exposes `aws_name_for_stack()` (never double-prefixes) + `sg_name_for_stack()` (always uses `-sg` suffix, never starts with reserved `sg-`). |

Used by: `elastic/`, `opensearch/`, `prometheus/`. Tests: `tests/unit/sgraph_ai_service_playwright__cli/aws/test_Stack__Naming.py` (9 cases).

---

## `deploy/` — SP CLI Lambda

Provisions the SP CLI as its own AWS Lambda (`sp-playwright-cli-{stage}`).

| File | Role |
|------|------|
| `deploy/images/sp_cli/dockerfile` | Base `public.ecr.aws/lambda/python:3.12` (no Chromium) |
| `deploy/SP__CLI__Lambda__Policy.py` | IAM inline policy dicts (5 policies; PassRole ARN-scoped) |
| `deploy/SP__CLI__Lambda__Role.py` | Creates/updates IAM role via `osbot-aws` |
| `deploy/Docker__SP__CLI.py` | ECR build + push |
| `deploy/Lambda__SP__CLI.py` | Lambda upsert + Function URL |
| `deploy/provision.py` | Orchestrator: role → image → Lambda |

Tests: 18 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/deploy/`.

---

## `ec2/` — EC2 Instance Lifecycle

Manages Playwright + agent_mitmproxy EC2 stacks. Exposes list/info/create/delete as both CLI commands and HTTP routes.

| Layer | Key classes |
|-------|-------------|
| service | `Ec2__AWS__Client` (AWS boundary), `Ec2__Service` (orchestrator adapter) |
| schemas | `Schema__Ec2__Create__Request`, `Schema__Ec2__Create__Response`, `Schema__Ec2__Instance__Info`, `Schema__Ec2__Delete__Response`, `Schema__Ec2__Preflight` |
| enums | `Enum__Instance__State` |
| primitives | `Safe_Str__Deploy_Name`, `Safe_Str__Instance__Id`, `Safe_Str__AMI__Id`, etc. |

HTTP routes: `GET /ec2/playwright/list`, `GET /ec2/playwright/info/{name}`, `POST /ec2/playwright/create`, `DELETE /ec2/playwright/delete/{name}`, `DELETE /ec2/playwright/delete-all`.

Tests: 24 unit tests (`test_Ec2__AWS__Client.py`) + 8 FastAPI TestClient tests.

---

## `elastic/` — Elastic/Kibana Stack + LETS Pipeline

The largest sub-package. See `03__lets-pipeline.md` and `04__elastic-stack.md` for detail.

| Sub-folder | Concern |
|------------|---------|
| `elastic/service/` | Kibana/ES stack management (`Elastic__Service`, `Elastic__AWS__Client`, `Elastic__HTTP__Client`, `Kibana__Saved_Objects__Client`) |
| `elastic/lets/cf/inventory/` | LETS slice 1 — S3 listing metadata → ES |
| `elastic/lets/cf/events/` | LETS slice 2 — `.gz` parse → ES |
| `elastic/lets/cf/consolidate/` | LETS slice 3 (C-stage) — many `.gz` → one `events.ndjson.gz` |
| `elastic/lets/cf/sg_send/` | LETS slice 4 — SG_Send sync orchestrator |
| `elastic/lets/runs/` | Pipeline run journal (`sg-pipeline-runs-*`) |

---

## `fast_api/` — SP CLI FastAPI App

| File | Role |
|------|------|
| `fast_api/Fast_API__SP__CLI.py` | Stand-alone FastAPI app; mounts EC2 + Observability + OpenSearch routes |
| `fast_api/lambda_handler.py` | Mangum wrapper for Lambda |
| `fast_api/exception_handlers.py` | `ValueError` → HTTP 422 bridge for all Type_Safe primitives |
| `fast_api/routes/Routes__Ec2__Playwright.py` | 5 EC2 endpoints |
| `fast_api/routes/Routes__Observability.py` | 3 observability endpoints |
| `opensearch/fast_api/routes/Routes__OpenSearch__Stack.py` | OpenSearch stack routes |

---

## `image/` — Shared Docker Image Build

Shared by the Playwright EC2 image builder and the SP CLI Lambda image builder.

| File | Role |
|------|------|
| `image/service/Image__Build__Service.py` | Stages a tempdir build context + calls Docker SDK |
| `image/schemas/Schema__Image__Build__Request.py` | Build inputs |
| `image/schemas/Schema__Image__Build__Result.py` | `image_id`, `image_tags`, `duration_ms` |

Tests: 15 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/image/`.

---

## `observability/` — AMP + OpenSearch + Grafana Read/Delete

Read-only surface for AWS-managed observability stacks.

| File | Role |
|------|------|
| `observability/service/Observability__AWS__Client.py` | boto3 boundary (AMP / OpenSearch / Grafana — osbot-aws wrappers not yet available) |
| `observability/service/Observability__Service.py` | Pure logic: `list_stacks`, `get_stack_info`, `delete_stack`, `resolve_region` |

Tests: 26 unit tests in `tests/unit/sgraph_ai_service_playwright__cli/observability/`.

---

## `opensearch/` — Ephemeral OpenSearch + Dashboards

Full lifecycle management for ephemeral single-node OpenSearch EC2 stacks.

| File | Role |
|------|------|
| `opensearch/service/OpenSearch__Service.py` | Orchestrator: create/list/get/delete/health |
| `opensearch/service/OpenSearch__AWS__Client.py` | AWS composition shell |
| `opensearch/service/OpenSearch__Compose__Template.py` | Renders docker-compose.yml |
| `opensearch/service/OpenSearch__User_Data__Builder.py` | Renders EC2 UserData bash |
| `opensearch/service/OpenSearch__Launch__Helper.py` | Runs the EC2 instance |
| `opensearch/cli/Renderers.py` | Typer output formatters |

131 unit tests. CLI: `sp os` / `sp opensearch`. HTTP routes on `Fast_API__SP__CLI`.

---

## `linux/` — Ephemeral Bare Linux EC2 Stacks

Ephemeral AL2023 EC2 stacks; SSM access only (no SSH). CLI: `sp linux`. Tag: `sg:purpose=linux`. Reuses `playwright-ec2` IAM instance profile.

| Layer | Key classes |
|-------|-------------|
| service | `Linux__Service`, `Linux__AWS__Client`, `Linux__SG__Helper`, `Linux__AMI__Helper`, `Linux__Instance__Helper`, `Linux__Launch__Helper`, `Linux__User_Data__Builder`, `Linux__Health__Checker` |
| schemas | `Schema__Linux__Create__Request/Response`, `Schema__Linux__Info`, `Schema__Linux__List`, `Schema__Linux__Delete__Response`, `Schema__Linux__Health__Response` |
| enums | `Enum__Linux__Stack__State` |
| primitives | `Safe_Str__Linux__Stack__Name`, `Safe_Str__IP__Address` |

HTTP routes: `POST /linux/stack`, `GET /linux/stacks`, `GET /linux/stack/{name}`, `DELETE /linux/stack/{name}`, `GET /linux/stack/{name}/health`.

---

## `docker/` — Ephemeral Docker-on-AL2023 EC2 Stacks

AL2023 EC2 stacks with Docker CE pre-installed; SSM access only. CLI: `sp docker`. Tag: `sg:purpose=docker`. Reuses `playwright-ec2` IAM instance profile. Health poll timeout 600 s (Docker CE install ~3 min).

| Layer | Key classes |
|-------|-------------|
| service | `Docker__Service`, `Docker__AWS__Client`, `Docker__SG__Helper`, `Docker__AMI__Helper`, `Docker__Instance__Helper`, `Docker__Launch__Helper`, `Docker__User_Data__Builder`, `Docker__Health__Checker` |
| schemas | `Schema__Docker__Create__Request/Response`, `Schema__Docker__Info`, `Schema__Docker__List`, `Schema__Docker__Delete__Response`, `Schema__Docker__Health__Response` |
| enums | `Enum__Docker__Stack__State` |
| primitives | `Safe_Str__Docker__Stack__Name`, `Safe_Str__IP__Address` |

HTTP routes: `POST /docker/stack`, `GET /docker/stacks`, `GET /docker/stack/{name}`, `DELETE /docker/stack/{name}`, `GET /docker/stack/{name}/health`.

---

## `prometheus/` — Prometheus Stack Foundation

Phase B step 6a — skeleton only; no full stack management yet.

| File | Role |
|------|------|
| `prometheus/service/Prometheus__AWS__Client.py` | Declares `PROM_NAMING` + tag constants |
| `prometheus/primitives/Safe_Str__Prom__Stack__Name.py` | Stack name primitive |
| `prometheus/enums/Enum__Prom__Stack__State.py` | Lifecycle state vocabulary |

19 unit tests. CLI planned as `sp prom` / `sp prometheus`.

---

## Cross-Links

- `03__lets-pipeline.md` — LETS pipeline (inventory / events / consolidate / sg-send)
- `04__elastic-stack.md` — Elastic/Kibana service layer
- `08__aws-and-infrastructure.md` — Lambda deploy, IAM policies
- `team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md` — canonical reality for this area
