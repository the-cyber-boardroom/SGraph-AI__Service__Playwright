# ═══════════════════════════════════════════════════════════════════════════════
# sg-uj-worker — Docker image (browser worker)
#
# One worker = one journey run. Same Microsoft Playwright base as the sg-playwright
# service (Chromium + system deps pre-installed), so the worker reuses the Playwright
# core (Step__Executor stays the only page.* caller). The conductor launches this image
# per replica, injecting the run identity + the journey as SG_UJ__* env (env-JSON
# delivery — no journey store). The CMD is Journey__Worker__Entrypoint.
#
# AUTHOR-ONLY / GATED: not built or run in this environment (no Docker daemon). Shipped
# for the deploy harness; exercise it with `sg_compute_specs/user_journey/tests/deploy/`.
#
# Build (from repo root):
#   docker build -f sg_compute_specs/user_journey/docker/worker/Dockerfile \
#                -t diniscruz/sg-uj-worker:v0.2.41 .
#
# Run (the conductor sets these; shown for a manual one-off):
#   docker run --rm \
#     -e SG_UJ__RUN_ID=local-1 \
#     -e SG_UJ__JOURNEY_JSON='{"journey_id":"checkout","target_url":"https://example.com/","steps":[{"action":"goto","url":"https://example.com/"}]}' \
#     -e SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://agent-mitmproxy:8080 \
#     diniscruz/sg-uj-worker:v0.2.41
# ═══════════════════════════════════════════════════════════════════════════════

FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TERM=xterm-256color

WORKDIR /app

# Reuse the proven sg-playwright requirements (same base image, same Chromium pin).
COPY sg_compute_specs/playwright/requirements.txt ./
RUN  python3 -m pip install -r requirements.txt --no-cache-dir

# Same build-time guard the service image uses: prove playwright landed in the CMD
# interpreter and matches the base-image tag (bump in lockstep with the FROM line).
RUN  python3 -c "import importlib.metadata as m; v=m.version('playwright'); \
                 assert v=='1.58.0', f'playwright {v} != 1.58.0 (base v1.58.0-noble)'; \
                 from playwright.sync_api import sync_playwright; print('guard OK', v)"

COPY sg_compute/        sg_compute/
COPY sg_compute_specs/  sg_compute_specs/
COPY capabilities.json  ./

CMD ["python3", "-m", "sg_compute_specs.user_journey.core.worker.Journey__Worker__Entrypoint"]
