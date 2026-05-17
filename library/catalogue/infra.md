---
title: "Catalogue — Infrastructure"
file: infra.md
shard: infra
as_of: v0.2.25
last_refreshed: 2026-05-17
maintainer: Librarian
prior_snapshot: (none — first snapshot)
---

# Catalogue — Infrastructure

Docker images, CI workflows, registries, deploy targets, EC2 provisioning, and observability. Cross-reference [`team/roles/librarian/reality/infra/`](../../team/roles/librarian/reality/) — VERIFY: not yet migrated; current shim is [`team/roles/librarian/reality/_archive/v0.1.31/03__docker-and-ci.md`](../../team/roles/librarian/reality/_archive/v0.1.31/03__docker-and-ci.md) + [`08__sp-cli-lambda-deploy.md`](../../team/roles/librarian/reality/_archive/v0.1.31/08__sp-cli-lambda-deploy.md).

---

## Docker Images

### Live images

| Image | Source | Registry | Notes |
|-------|--------|----------|-------|
| `diniscruz/sg-playwright:{version}` | `sg_compute_specs/playwright/Dockerfile` | **Docker Hub** | Microsoft Playwright base (`mcr.microsoft.com/playwright/python:v1.58.0-noble`). Build-time guard asserts `playwright==1.58.0`. CMD: `python3 -m sg_compute_specs.playwright.core.fast_api.lambda_handler`. EXPOSE 8000. |
| Host control plane (`sgraph_ai_service_playwright_host:latest`) | `docker/host-control/Dockerfile` | **ECR** (`{account}.dkr.ecr.{region}.amazonaws.com/sgraph_ai_service_playwright_host`) | `python:3.12-alpine` + uvicorn. Runs inside every ephemeral EC2 instance as the host-plane sidecar. Port mapping: container `:8000` → host `:19009`. |
| Local Claude sidecar | `docker/local-claude/Dockerfile` | local-only | `node:22-bookworm-slim`. Drives the laptop-local Claude → Ollama LiteLLM bridge — see `docker/local-claude/docker-compose.yml`. |

### Per-spec Dockerfiles

Per-spec images for stacks that need them live under each spec, e.g. `sg_compute_specs/{vault_app,mitmproxy,…}/docker/`. The Playwright Dockerfile is special — it ships the service itself rather than a stack sidecar.

### Retired

- **Playwright Lambda + ECR image.** Retired in v0.2.11 (`team/roles/architect/reviews/05/14/v0.2.6__playwright-deployment-simplification.md`). The previous `sg-playwright:{stage}` Lambda + `sg-playwright` ECR repo are gone; the service now ships as the Docker Hub image above.
- **SP CLI Lambda (`sp-playwright-cli-{stage}`).** Retired alongside the duality refactor — `Fast_API__SP__CLI` is now mounted at `/legacy` under `Fast_API__Compute` (BV2.10, 2026-05-05).
- **`agent_mitmproxy` Docker image.** Retired in BV2.12 (2026-05-05); replaced by the per-spec `sg_compute_specs/mitmproxy/`.

---

## CI Workflows (`.github/workflows/`)

| File | Trigger | Purpose |
|------|---------|---------|
| `ci-pipeline.yml` | `workflow_call` (called by the per-target wrappers) | Reusable base pipeline. Jobs: `run-unit-tests`, `check-aws-credentials`, `detect-changes` (path filter: playwright-image / host-image), `increment-tag` (dev/main only), `build-and-push-playwright-image` (multi-arch → Docker Hub `diniscruz/sg-playwright`), `build-and-push-host-image` (→ ECR). |
| `ci-pipeline__dev.yml` | push to `dev` | Wraps `ci-pipeline.yml` with dev defaults. |
| `ci-pipeline__main.yml` | push to `main` | Wraps `ci-pipeline.yml` with main defaults. |
| `ci-pipeline__prod.yml` | push to `prod` (or manual) | Wraps `ci-pipeline.yml` with prod defaults. |
| `ci__host_control.yml` | `workflow_dispatch` only | Manual / emergency rebuild for the host-control image. Routine builds now flow through `ci-pipeline.yml`'s `build-and-push-host-image` job. |
| `bake-ami.yml` | `workflow_dispatch` or `workflow_call` from `ci-pipeline.yml` | Two-phase EC2 AMI bake: Phase 1 fresh AL2023 install → health + smoke → snapshot; Phase 2 verify from snapshot → tag healthy. VERIFY: doc references "ECR image URI" inputs which suggests Phase 1 still loads images from ECR (consistent with the host-control image flow). |

> Disabled jobs in earlier `ci-pipeline.yml` revisions (`run-integration-tests`, `deploy-lambda`, `smoke-test`) — Lambda deploy and smoke-test are gone since v0.2.11. Integration tests remain gated on Chromium availability.

---

## Registries

| Registry | Used for |
|----------|---------|
| Docker Hub (`diniscruz/`) | Playwright service image (sole production registry path). |
| ECR (`{account}.dkr.ecr.{region}.amazonaws.com/sgraph_ai_service_playwright_host`) | Host-control image. EC2 instances pull from ECR via SSM/instance profile. |
| ECR (per-spec, ephemeral) | Some specs publish to ECR if their EC2 user-data pulls private images. VERIFY: list under `sg_compute_specs/*/docker/`. |

Retired: `sg-playwright` and `sp-playwright-cli` ECR repos (per the v0.2.11 simplification).

---

## EC2 Provisioning

| Surface | File | Notes |
|---------|------|-------|
| Direct EC2 provisioner | `scripts/provision_ec2.py` (2,510 LOC — `INC-003`) | Wraps `Ec2__AWS__Client` helpers. Used for the Playwright + sidecar stack and the host-control plane install. |
| Spec-level EC2 platform | `sg_compute/platforms/ec2/` | `EC2__Platform`, `Launch__Helper`, `SG__Helper`, `Tags__Builder`, `AMI__Helper`, `Instance__Helper`, `Stack__Mapper`, `Stack__Naming`, `Health__Poller`, `HTTP__Probe`. |
| Per-spec EC2 helpers | `sg_compute_specs/{spec}/service/*__AWS__Client.py` and `*__User_Data__Builder.py` | Each STABLE spec composes user-data via `platforms/ec2/user_data/Section__*` modules (`Section__Base`, `Section__Docker`, `Section__Node`, `Section__Nginx`, `Section__Env__File`, `Section__Shutdown`, `Section__Sidecar` (BV2.2), `Section__GPU_Verify`, `Section__Ollama`, `Section__Claude_Launch`, `Section__Agent_Tools`). |
| Sidecar | `Section__Sidecar` | Installs the host-control image on every Node so every stack exposes the uniform `/containers/*`, `/shell/*`, `/host/*` surface. |

EC2 stack-name convention: `{section}-{adjective}-{scientist}` (e.g. `elastic-quiet-fermi`). Generated by `Random__Stack__Name__Generator` (pools shared across sections by design).

---

## AWS Resource Inventory

| Resource | Name pattern | Owner |
|----------|--------------|-------|
| Docker Hub image | `diniscruz/sg-playwright:{version}` | Playwright service |
| ECR repo | `sgraph_ai_service_playwright_host` | Host control plane |
| EC2 (tagged `sg:purpose=playwright`) | `playwright-{adjective}-{scientist}` | `sg playwright create` |
| EC2 (tagged `sg:purpose=elasticsearch`) | `elastic-…` | `sg elastic create` |
| EC2 (tagged `sg:purpose=opensearch`) | `opensearch-…` | `sg opensearch create` |
| EC2 (tagged `sg:purpose=docker`) | `docker-…` | `sg docker create` |
| EC2 (tagged `sg:purpose=podman`) | `podman-…` | `sg podman create` |
| EC2 (tagged `sg:purpose=ollama`) | `ollama-…` | `sg ollama create` |
| EC2 (other spec purposes) | `{spec}-…` | per spec |
| S3 (SGraph CloudFront logs bucket) | externally managed | LETS pipeline source |
| IAM instance profile | `sg-playwright-ec2` / `playwright-ec2` | SSM + ECR pull + CloudWatch |
| AMP / OpenSearch / Grafana | `sg-*` | `sg observability` (READ + DELETE only) |
| Route 53 zones | externally managed | `sg aws dns` |
| ACM certs | externally managed | `sg aws acm` |
| CloudFront distributions | per `vault_publish` spec | `sg aws cf` |
| Lambda functions | per `vault_publish` spec (Waker Lambda) | `sg aws lambda` |
| SSM parameters | `/vault-publish/{slug}/...` | `vault_publish` slug registry |

---

## Security Group Naming Rules (`INC-001`)

**Never** start a security-group `GroupName` with `sg-` — AWS reserves `sg-*` for security-group IDs and rejects `CreateSecurityGroup`. Use suffix `{stack}-sg`. Use `Stack__Naming.sg_name_for_stack()` to generate compliant names. `GroupDescription` must be ASCII-only. Precedents: `scripts/provision_ec2.py:83` (`SG__NAME = 'playwright-ec2'`), `sgraph_ai_service_playwright__cli/elastic/service/Elastic__AWS__Client.py`.

## AWS Name Tag — No Double-Prefix (`INC-002`)

When the logical name already carries the section prefix (e.g. `elastic-quiet-fermi`), do NOT wrap it again into `elastic-elastic-quiet-fermi`. Use `Stack__Naming.aws_name_for_stack()` which prefixes only when missing.

---

## Observability Stack

`scripts/provision_ec2.py`'s `COMPOSE_YAML_TEMPLATE` includes: `prometheus`, `grafana`, `cadvisor`, `node-exporter`, `loki`, `promtail`, `cloudwatch-agent`, `xray-daemon`. Config files written to `/opt/sg-playwright/config/` via UserData heredoc. IAM role extended with CloudWatch, X-Ray, and Prometheus Remote Write policies.

OpenSearch and Prometheus also ship as their own ephemeral specs (`sg opensearch`, `sg prometheus`) — independent of the in-EC2 observability sidecars.

---

## Secrets — Where They Live

| Kind | Home |
|------|------|
| AWS credentials | GH Actions repo secrets: `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `AWS_ACCOUNT_ID` |
| Docker Hub PAT | GH Actions repo secret: `DOCKERHUB_TOKEN` (for `diniscruz/` namespace) |
| Service API keys | GH Actions secret: `FAST_API__AUTH__API_KEY__VALUE` |
| Vault keys | Shared out-of-band — never committed to git |
| `.env` files | `.env.example` is a template only — never commit actual keys |

---

## Cross-Links

- CI pipeline spec (detail): [`library/docs/specs/v0.20.55__ci-pipeline.md`](../docs/specs/v0.20.55__ci-pipeline.md)
- Reality (Infra domain — pending migration): [`team/roles/librarian/reality/_archive/v0.1.31/03__docker-and-ci.md`](../../team/roles/librarian/reality/_archive/v0.1.31/03__docker-and-ci.md)
- Host control plane reality: [`team/roles/librarian/reality/host-control/index.md`](../../team/roles/librarian/reality/host-control/index.md)
- Tests (deploy-via-pytest): [`tests.md`](tests.md)
