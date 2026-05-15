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
# Use `python3 -m pip` (not `python -m pip`) so the install target matches the
# CMD interpreter below. In some Microsoft playwright base-image tags `python`
# and `python3` resolve to different interpreters with separate site-packages —
# installing under `python` then running under `python3` produces a runtime
# ModuleNotFoundError even though pip succeeded.
RUN  python3 -m pip install -r requirements.txt --no-cache-dir

# Build-time guard — this is the regression this layer prevents from re-shipping.
# Runs in the same `python3` interpreter as CMD below, so a successful guard is
# proof that runtime imports will succeed. Version-comparison is normalised
# with packaging.version so wheel metadata suffixes (e.g. '1.58.0.post1') don't
# break the assertion — the requirements.txt pin is the source of truth for
# the exact version; this guard just verifies the install ended up in the
# right interpreter and matches the major.minor.patch we asked for.
# When bumping the base image (FROM line above), bump the pin in
# requirements.txt AND the literal below in lockstep — all three must move
# together.
RUN  python3 -m pip show playwright
RUN  python3 -c "import sys; print('python:', sys.executable, sys.version); \
                 import playwright; print('playwright at:', playwright.__file__, 'version:', playwright.__version__); \
                 from playwright.sync_api import sync_playwright; \
                 from packaging.version import Version; \
                 assert Version(playwright.__version__).release[:3] == (1, 58, 0), \
                        f'playwright {playwright.__version__} not in the 1.58.0 family (base image v1.58.0-noble)'; \
                 print('build-time guard OK')"

COPY sg_compute/        sg_compute/
COPY sg_compute_specs/  sg_compute_specs/
COPY capabilities.json  ./

EXPOSE 8000

CMD ["python3", "-m", "sg_compute_specs.playwright.core.fast_api.lambda_handler"]
