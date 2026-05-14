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

COPY sg_compute/        sg_compute/
COPY sg_compute_specs/  sg_compute_specs/
COPY capabilities.json  ./

EXPOSE 8000

CMD ["python3", "-m", "sg_compute_specs.playwright.core.fast_api.lambda_handler"]
