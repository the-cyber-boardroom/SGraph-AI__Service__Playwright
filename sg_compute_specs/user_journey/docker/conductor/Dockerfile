# ═══════════════════════════════════════════════════════════════════════════════
# sg-uj-conductor — Docker image (suite control plane)
#
# Runs Fast_API__Conductor under uvicorn (NOT Lambda — it launches worker containers,
# which the LWA/Function-URL adapter can't host). No browser, so a lean python base +
# the docker CLI (the conductor shells `docker run` against the mounted host socket).
# Boot swaps the suite runtime to the Docker backend when a daemon is reachable.
#
# AUTHOR-ONLY / GATED: not built or run in this environment (no Docker daemon). Shipped
# for the deploy harness; exercise it with `sg_compute_specs/user_journey/tests/deploy/`.
#
# Build (from repo root):
#   docker build -f sg_compute_specs/user_journey/docker/conductor/Dockerfile \
#                -t diniscruz/sg-uj-conductor:v0.2.41 .
#
# Run (mount the host docker socket so it can launch workers; point at the sidecar):
#   docker run -p 8000:8000 \
#     -v /var/run/docker.sock:/var/run/docker.sock \
#     -e FAST_API__AUTH__API_KEY__VALUE=<key> \
#     -e SG_UJ__CAPTURE_URL=http://agent-mitmproxy:8000 \
#     diniscruz/sg-uj-conductor:v0.2.41
# ═══════════════════════════════════════════════════════════════════════════════

FROM python:3.12-slim

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# docker CLI only (the daemon is the host's, via the mounted socket).
RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY sg_compute_specs/user_journey/docker/conductor/requirements.txt ./
RUN  python3 -m pip install -r requirements.txt --no-cache-dir

COPY sg_compute/        sg_compute/
COPY sg_compute_specs/  sg_compute_specs/

EXPOSE 8000

CMD ["python3", "-m", "sg_compute_specs.user_journey.core.conductor.api.conductor_app"]
