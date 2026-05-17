# infra — Reality Index

**Domain:** `infra/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** consolidated from `_archive/v0.1.31/03__docker-and-ci.md` + `08__sp-cli-lambda-deploy.md`.

Docker images, CI/CD pipelines, ECR, Lambda deploy machinery, EC2 provisioning. Covers three image families today (Playwright service, agent_mitmproxy, sp-playwright-cli) plus one sidecar (host-control — see [`host-control/index.md`](../host-control/index.md)).

---

## EXISTS (code-verified)

### Playwright service image

- Dockerfile bakes `capabilities.json` into `/var/task/` and writes an `image_version` file (since v0.1.29). Base: `mcr.microsoft.com/playwright/python:v1.58.0-noble`; Lambda Web Adapter 1.0.0.
- Build + push via pytest: `tests/docker/test_Build__Docker__SGraph-AI__Service__Playwright.py` + `tests/docker/test_ECR__Docker__SGraph-AI__Service__Playwright.py`.
- `Build__Docker__SGraph_AI__Service__Playwright.build_docker_image()` stages the build context in a tempdir and calls the Docker SDK directly (bypasses the `@catch`-wrapped `Docker_Image.build` so real failures surface).
- Phase-A step-2 refactor (see [`cli/duality.md`](../cli/duality.md)) shifted build orchestration into the shared `Image__Build__Service`; the Playwright Build class now composes 3 stage items (`lambda_entry.py`, `image_version`, `sgraph_ai_service_playwright`).

### Playwright CI pipeline

- `.github/workflows/ci-pipeline.yml` — reusable, called by `ci-pipeline__dev.yml` / `__main.yml` / `__prod.yml`.

Active jobs:

| Job | What it does |
|-----|--------------|
| `run-unit-tests` | `tests/unit/`, Python 3.12 |
| `check-aws-credentials` | Gates every AWS-touching job |
| `detect-changes` | `dorny/paths-filter@v3` narrowed to `Dockerfile`, `requirements.txt`, `lambda_entry.py`, `sgraph_ai_service_playwright/docker/images/**`. Changes under `sgraph_ai_service_playwright/docker/*.py` (deploy-time helpers) no longer force a rebuild. |
| `build-and-push-image` | Single job, no tar save/reload. Gated on `detect-changes.image-rebuild-needed == 'true' || inputs.force_image_rebuild` |
| `increment-tag` | `dev` bumps minor, `main` bumps major, `prod` skipped |
| `deploy-code` | S3 zip upload via `scripts/deploy_code.py` |
| `provision-lambdas` | v0.1.31 — upserts `sg-playwright-baseline-<stage>` + `sg-playwright-<stage>` via `scripts/provision_lambdas.py --mode=<full\|code-only>`. Mode = `full` when image was just rebuilt; `code-only` when reusing existing ECR image (saves ~30–60 s on image-pull wait) |

Disabled jobs (`if: false`): `run-integration-tests`, `deploy-lambda`, `smoke-test` — superseded by the S3-zip + `/admin/health` smoke inside `deploy_code.py`.

---

### agent_mitmproxy image (v0.1.32)

- `agent_mitmproxy/docker/images/agent_mitmproxy/dockerfile` — `python:3.12-slim` + supervisor + ca-certificates + curl. `EXPOSE 8080 8000`. `CMD ["/app/entrypoint.sh"]`.
- Build context is the **repo root** (`docker build -f agent_mitmproxy/docker/images/agent_mitmproxy/dockerfile .`). All COPY paths rooted there.
- `entrypoint.sh` seeds `/app/current_interceptor.py` from baked default if absent, then `exec supervisord`.
- `supervisord.conf` runs `mitmweb` + `uvicorn` as siblings; both `autorestart=true`; logs to container stdout/stderr.
- Helper classes: `agent_mitmproxy/docker/Docker__Agent_Mitmproxy__Base.py` (wires `Create_Image_ECR`), `ECR__Docker__Agent_Mitmproxy.py` (push + Docker Desktop `credsStore: desktop` workaround).

### agent_mitmproxy CI

`.github/workflows/ci__agent_mitmproxy.yml` — **separate from the Playwright pipeline**. Paths-filter scopes every trigger (`push` to `dev`/`main`, `pull_request`, `workflow_dispatch`) to `agent_mitmproxy/**`, `scripts/provision_mitmproxy_ec2.py`, `tests/unit/agent_mitmproxy/**`, `tests/unit/scripts/test_provision_mitmproxy_ec2.py`, and the workflow file itself.

Jobs:

| Job | What it does |
|-----|--------------|
| `run-unit-tests` | pytest against `tests/unit/agent_mitmproxy/` + `tests/unit/scripts/test_provision_mitmproxy_ec2.py`, Python 3.12 |
| `check-aws-credentials` | Gate for image-push |
| `detect-changes` | Image rebuild filter scoped to `agent_mitmproxy/{requirements.txt, addons, consts, fast_api, schemas, docker/images, version, __init__.py}` |
| `build-and-push-image` | `docker build` with repo-root context, then `ECR__Docker__Agent_Mitmproxy().setup().ecr_setup() + .publish_docker_image()` via `python -c` |

EC2 deploy intentionally **not** wired into CI. Runs on-demand via `python scripts/provision_mitmproxy_ec2.py`.

> **Post-v0.1.31 note:** BV2.12 (2026-05-05) deleted `ci__agent_mitmproxy.yml` along with the package. **VERIFY** before quoting as current.

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

### EC2 provisioning — unified

`scripts/provision_ec2.py` (v0.1.33 unified) — replaces the two earlier spike scripts.

- **Instance type:** t3.large.
- **AMI:** AL2023 (latest, via SSM param).
- **IAM role:** `sg-playwright-ec2` (attaches `AmazonEC2ContainerRegistryReadOnly` + `AmazonSSMManagedInstanceCore`).
- **SG:** `playwright-ec2` — opens `:8000` (Playwright) + `:8001` (agent_mitmproxy admin). Sidecar proxy `:8080` stays internal to docker-network.
- **UserData:** installs `docker docker-compose-plugin`, logs into ECR, pulls both images, writes `/opt/sg-playwright/docker-compose.yml` inline, runs `docker compose up -d`. 120 s watchdog.
- **`--terminate`:** tears down by `Name=sg-playwright-ec2` tag.

Sister sections (`sp os`, `sp prom`, `sp vnc`) each have their own SG/AMI/UserData via their `{Section}__SG__Helper`, `{Section}__AMI__Helper`, `{Section}__User_Data__Builder` — see [`cli/duality.md`](../cli/duality.md).

Tests: `tests/unit/scripts/test_provision_ec2.py` (19 tests).

---

### Repository compose / .env

- `docker-compose.yml` (repo root) — brings up Playwright + agent_mitmproxy on shared `sg-net` bridge. Playwright on host `:8000`, sidecar admin API on host `:8001`, sidecar proxy `:8080` Docker-network-only. Env: `SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://agent-mitmproxy:8080` + `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS=true`.
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
