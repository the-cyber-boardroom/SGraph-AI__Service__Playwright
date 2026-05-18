# infra — Reality Index

**Domain:** `infra/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** consolidated from `_archive/v0.1.31/03__docker-and-ci.md` + `08__sp-cli-lambda-deploy.md`.

Docker images, CI/CD pipelines, ECR, Lambda deploy machinery, EC2 provisioning. Covers three image families today (Playwright service, agent_mitmproxy, sp-playwright-cli) plus one sidecar (host-control — see [`host-control/index.md`](../host-control/index.md)).

---

## EXISTS (code-verified)

### Playwright service image

- Dockerfile bakes `capabilities.json` into `/var/task/` and writes an `image_version` file (since v0.1.29). Base: `mcr.microsoft.com/playwright/python:v1.58.0-noble`. Lambda Web Adapter was dropped post v0.2.11 — the service now ships as a Docker Hub image (`diniscruz/sg-playwright`) consumed by EC2, not Lambda.
- Build path: `ci-pipeline.yml` builds the image per-architecture on native GitHub runners (`linux/amd64` on `ubuntu-latest`, `linux/arm64` on `ubuntu-24.04-arm`), pushes BY DIGEST, then a merge job publishes the multi-arch tag. No QEMU emulation.
- Path-gated on `sg_compute_specs/playwright/**` + `sg_compute/**` so unrelated changes skip the rebuild.

### Playwright CI pipeline

- `.github/workflows/ci-pipeline.yml` — reusable, called by `ci-pipeline__dev.yml` / `__main.yml` / `__prod.yml`.

Active jobs:

| Job | What it does |
|-----|--------------|
| `run-unit-tests` | `pytest tests/ci/` (CI guards) + `pytest tests/unit/`, Python 3.12 |
| `check-aws-credentials` | Gates only the `host-control` ECR push job — the Playwright image goes to Docker Hub and doesn't need AWS creds |
| `detect-changes` | `dorny/paths-filter@v3` with two filters: `playwright-image` (`sg_compute_specs/playwright/**`, `sg_compute/**`) and `host-image` (`sg_compute/**`, `docker/host-control/**`) |
| `increment-tag` | `dev` bumps minor, `main` bumps major, `prod` skipped; syncs the bumped version into `sg_compute/version` + `sg_compute/pyproject.toml` |
| `build-playwright-image` | Matrix per-arch native build → Docker Hub by digest; merge job tags the multi-arch manifest |
| `build-and-push-host-image` | Builds the host-control image to ECR (separate concern from the Playwright image) |

The Playwright Lambda / ECR / S3-zip jobs were **retired in v0.2.11** — see `team/roles/architect/reviews/05/14/v0.2.6__playwright-deployment-simplification.md`.

---

### agent_mitmproxy image (package v0.1.33; post-BV2.12 location)

- `sg_compute_specs/mitmproxy/docker/images/agent_mitmproxy/dockerfile` — `python:3.12-slim` + supervisor + ca-certificates + curl. `EXPOSE 8080 8000`. `CMD ["/app/entrypoint.sh"]`.
- Build context is the **repo root** (`docker build -f sg_compute_specs/mitmproxy/docker/images/agent_mitmproxy/dockerfile .`). All COPY paths rooted there.
- `entrypoint.sh` seeds `/app/current_interceptor.py` from baked default if absent, then `exec supervisord`.
- `supervisord.conf` runs `mitmweb` + `uvicorn` as siblings; both `autorestart=true`; logs to container stdout/stderr.
- Helper classes: `sg_compute_specs/mitmproxy/docker/Docker__Agent_Mitmproxy__Base.py` (wires `Create_Image_ECR`), `ECR__Docker__Agent_Mitmproxy.py` (push + Docker Desktop `credsStore: desktop` workaround).

### agent_mitmproxy CI

The standalone `.github/workflows/ci__agent_mitmproxy.yml` was **deleted in BV2.12 (2026-05-05)** along with the orphan `agent_mitmproxy/` package and `scripts/provision_mitmproxy_ec2.py`. Confirmed by `ls .github/workflows/`: only `bake-ami.yml`, `ci-pipeline.yml`, `ci-pipeline__{dev,main,prod}.yml`, and `ci__host_control.yml` remain.

Today the mitmproxy package is exercised by:

- `ci-pipeline.yml` → `run-unit-tests` job — `pytest tests/unit/` picks up the in-package `sg_compute_specs/mitmproxy/tests/` suite via the repo-level editable install (12 files / 39 tests — see [`qa/index.md`](../qa/index.md)).
- No dedicated CI job rebuilds the mitmproxy image. The image lives in ECR as `agent_mitmproxy` and is pushed on-demand via `ECR__Docker__Agent_Mitmproxy().setup().publish_docker_image()`. Pulled at EC2 launch time when `sg-compute spec playwright create --with-mitmproxy` is used.

EC2 deploy intentionally **not** wired into CI — the sidecar lands as part of `Playwright__Compose__Template`'s 3-container shape.

---

### sp-playwright-cli image + Lambda deploy

Full detail in [`cli/ec2.md`](../cli/ec2.md). Summary:

- Base: `public.ecr.aws/lambda/python:3.12` (no Chromium).
- Handler: `sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler`.
- IAM role `sp-playwright-cli-lambda` with 5 inline `sp-cli-*` policies (ec2-management, iam-passrole, ecr-read, sts-helpers, observability).
- Lambda settings: 1024 MB / 120 s / x86_64 / Function URL AuthType=NONE (app-layer API-key middleware).
- Provision orchestrator: `python -m sgraph_ai_service_playwright__cli.deploy.provision --stage dev` (idempotent).
- CI workflow: `.github/workflows/ci__sp_cli.yml`. Stage resolution: `main` → `prod`; any other branch → `dev`; `workflow_dispatch` input wins.

---

### Host-control image

See [`host-control/index.md`](../host-control/index.md). Summary:

- `docker/host-control/Dockerfile` — Python 3.12 Alpine + `uvicorn`. Entrypoint runs `Fast_API__Host__Control` on `:8000` inside container, mapped to `:19009` on host.
- `docker/host-control/requirements.txt` — FastAPI, uvicorn, osbot-utils, osbot-fast-api, optional psutil. No Chromium, no Playwright, no AWS SDK.
- Built via `ci-pipeline.yml` (post BV2.1); `ci__host_control.yml` no longer tests the orphan package.

---

### EC2 provisioning — spec-driven (current)

The unified `scripts/provision_ec2.py` and the earlier `scripts/provision_mitmproxy_ec2.py` were **both removed** when EC2 lifecycle moved into the spec service layer. Today launches are driven by `sg-compute spec playwright create [--with-mitmproxy]`:

- **Instance type:** `t3.medium` default (set in `sg_compute_specs/playwright/service/Playwright__Service.py` — `DEFAULT_INSTANCE_TYPE`).
- **IAM profile:** `playwright-ec2` (SSM + ECR read).
- **AMI / SG:** resolved per-launch by `Playwright__AMI__Helper` + `Playwright__AWS__Client`.
- **UserData:** built by `Playwright__User_Data__Builder`; installs Docker, logs into ECR (for host-plane + optional mitmproxy), writes `/opt/sg-playwright/docker-compose.yml` (rendered by `Playwright__Compose__Template`), runs `docker compose up -d`.
- **Published host ports:** `:8000` (sg-playwright) always; `:8001` (mitmproxy admin) only with `--with-mitmproxy`. Host-plane sidecar stays on the internal `sg-net` bridge; mitmproxy proxy `:8080` is docker-network-only.
- **Terminate:** `sg-compute spec playwright delete <stack>`; stacks tagged via `Playwright__Stack__Mapper` (`STACK_TYPE`, `TAG_API_KEY`, `TAG_TERMINATE_AT`, `TAG_WITH_MITMPROXY`).

Sister specs (`docker`, `podman`, `prometheus`, `opensearch`, `vnc`, `elastic`, `firefox`, `neko`) follow the same pattern under their own `sg_compute_specs/<spec>/service/`.

---

### Repository compose / .env

- The repo-root `docker-compose.yml` was retired alongside the spike provisioners — compose files are now generated per-launch by `Playwright__Compose__Template` and written to the EC2 host's `/opt/sg-playwright/`. (Compose files still live under `docker/local-claude/` and `sg_compute_specs/vault_app/docker/compose/` for unrelated subsystems.)
- `.env.example` (repo root) — template for ECR registry, API key, optional upstream forwarding vars. **No AWS credentials**, **no vault keys** (CLAUDE.md rules 12-13).

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Sources: [`_archive/v0.1.31/03__docker-and-ci.md`](../_archive/v0.1.31/03__docker-and-ci.md), [`_archive/v0.1.31/08__sp-cli-lambda-deploy.md`](../_archive/v0.1.31/08__sp-cli-lambda-deploy.md)
- CLI Lambda detail: [`cli/ec2.md`](../cli/ec2.md)
- Host-control image + EC2 USER_DATA host-control block: [`host-control/index.md`](../host-control/index.md)
- QA test inventory (deploy tests, image build tests): [`qa/index.md`](../qa/index.md)
- Security rules (SG naming, AMI tag, no creds in git): [`security/index.md`](../security/index.md)
