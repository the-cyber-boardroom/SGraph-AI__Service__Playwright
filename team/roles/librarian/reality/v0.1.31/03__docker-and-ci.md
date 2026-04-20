# Docker + CI — Reality (v0.1.31 / v0.1.32)

See [README.md](README.md) for the index and split rationale.

---

## Playwright image

- Dockerfile bakes `capabilities.json` into `/var/task/` and writes an `image_version` file (since v0.1.29). Base: `mcr.microsoft.com/playwright/python:v1.58.0-noble`; Lambda Web Adapter 1.0.0.
- Build + push via pytest: `tests/docker/test_Build__Docker__SGraph-AI__Service__Playwright.py` + `tests/docker/test_ECR__Docker__SGraph-AI__Service__Playwright.py`.
- Docker infrastructure classes unchanged class-wise since v0.1.24. `Build__Docker__SGraph_AI__Service__Playwright.build_docker_image()` stages the build context in a tempdir and calls the Docker SDK directly (bypasses the `@catch`-wrapped `Docker_Image.build` so real failures surface).

## Playwright CI

- `.github/workflows/ci-pipeline.yml` (reusable, called by `ci-pipeline__dev.yml` / `__main.yml` / `__prod.yml`).
- Active jobs:
  - `run-unit-tests` — `tests/unit/`, Python 3.12.
  - `check-aws-credentials` — gates every AWS-touching job.
  - `detect-changes` — `dorny/paths-filter@v3` narrowed to `Dockerfile`, `requirements.txt`, `lambda_entry.py`, `sgraph_ai_service_playwright/docker/images/**`. Changes under `sgraph_ai_service_playwright/docker/*.py` (deploy-time helpers) no longer force a rebuild.
  - `build-and-push-image` — single job, no tar save/reload. Gated on `detect-changes.image-rebuild-needed == 'true' || inputs.force_image_rebuild`.
  - `increment-tag` — `dev` bumps minor, `main` bumps major, `prod` skipped.
  - `deploy-code` — S3 zip upload via `scripts/deploy_code.py`.
  - `provision-lambdas` — v0.1.31 — upserts `sg-playwright-baseline-<stage>` + `sg-playwright-<stage>` via `scripts/provision_lambdas.py --mode=<full|code-only>`. Mode = `full` when the image was just rebuilt; `code-only` when reusing the existing ECR image (saves ~30–60 s on the image-pull wait).
- Disabled jobs (`if: false`): `run-integration-tests`, `deploy-lambda`, `smoke-test` (superseded by the S3-zip + `/admin/health` smoke inside `deploy_code.py`).

---

## agent_mitmproxy image (v0.1.32)

- `agent_mitmproxy/docker/images/agent_mitmproxy/dockerfile` — `python:3.12-slim` + supervisor + ca-certificates + curl. `EXPOSE 8080 8000`. `CMD ["/app/entrypoint.sh"]`.
- Build context is the **repo root** (`docker build -f agent_mitmproxy/docker/images/agent_mitmproxy/dockerfile .`). All COPY paths are rooted there.
- `entrypoint.sh` seeds `/app/current_interceptor.py` from the baked default if absent, then `exec supervisord`.
- `supervisord.conf` runs `mitmweb` + `uvicorn` as siblings; both `autorestart=true`; logs to container stdout/stderr.
- Helper classes: `agent_mitmproxy/docker/Docker__Agent_Mitmproxy__Base.py` (wires `Create_Image_ECR`), `ECR__Docker__Agent_Mitmproxy.py` (push + Docker Desktop `credsStore: desktop` workaround).

## agent_mitmproxy CI

- `.github/workflows/ci__agent_mitmproxy.yml` — **separate from the Playwright pipeline**. Paths-filter scopes every trigger (`push` to `dev`/`main`, `pull_request`, `workflow_dispatch`) to `agent_mitmproxy/**`, `scripts/provision_mitmproxy_ec2.py`, `tests/unit/agent_mitmproxy/**`, `tests/unit/scripts/test_provision_mitmproxy_ec2.py`, and the workflow file itself.
- Jobs:
  - `run-unit-tests` — pytest against `tests/unit/agent_mitmproxy/` + `tests/unit/scripts/test_provision_mitmproxy_ec2.py`, Python 3.12.
  - `check-aws-credentials` — gate for the image-push job.
  - `detect-changes` — image rebuild filter scoped to `agent_mitmproxy/{requirements.txt, addons, consts, fast_api, schemas, docker/images, version, __init__.py}`.
  - `build-and-push-image` — `docker build` with repo-root context, then `ECR__Docker__Agent_Mitmproxy().setup().ecr_setup() + .publish_docker_image()` via `python -c`.
- EC2 deploy intentionally **not** wired into CI. Runs on-demand via `python scripts/provision_mitmproxy_ec2.py`.
