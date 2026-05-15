# ═══════════════════════════════════════════════════════════════════════════════
# sg-playwright — Docker image (v0.2 — Docker Hub, no Lambda Web Adapter)
#
# One image, run anywhere: laptop / CI / EC2 (host-plane pods) / Fargate.
# Base: Microsoft Playwright image (Chromium + system deps pre-installed).
# No LWA, no lambda_entry.py, no /var/task. Plain OCI container.
#
# Build (from repo root):
#   docker build -f sg_compute_specs/playwright/Dockerfile \
#                -t diniscruz/sg-playwright:<version> .
#
# Run:
#   docker run -p 8000:8000 \
#     -e FAST_API__AUTH__API_KEY__VALUE=<key> \
#     diniscruz/sg-playwright:<version>
# ═══════════════════════════════════════════════════════════════════════════════

FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app

COPY sg_compute_specs/playwright/requirements.txt ./
RUN  python -m pip install -r requirements.txt --no-cache-dir

# Build-time guard — this is the regression this layer prevents from re-shipping:
#   1. The python `playwright` module imports.
#   2. Its version matches the base-image tag (the wheel's Node driver protocol
#      must align with the Chromium revision bundled in /ms-playwright/).
#   3. The bundled Chromium binary exists where playwright expects it.
# When bumping the base image (FROM line above), bump the literal below AND the
# pin in requirements.txt in lockstep — all three must move together.
RUN  python3 -c "import playwright; \
                 from playwright.sync_api import sync_playwright; \
                 assert playwright.__version__ == '1.58.0', \
                        f'playwright {playwright.__version__} != base image 1.58.0'; \
                 print('build-time guard OK: playwright', playwright.__version__)"

COPY sg_compute/        sg_compute/
COPY sg_compute_specs/  sg_compute_specs/
COPY capabilities.json  ./

EXPOSE 8000

CMD ["python3", "-m", "sg_compute_specs.playwright.core.fast_api.lambda_handler"]
