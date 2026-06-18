# ─────────────────────────────────────────────────────────────────────────────
# TEMPORARY workaround image — adds httpx to the MITM service image.
#
# The upstream diniscruz/mgraph-ai-service-mitmproxy crashes at boot because
# osbot_fast_api's registry imports starlette.testclient, which requires httpx,
# and the image ships without it. This derived image just installs httpx and
# keeps the upstream ENTRYPOINT/CMD untouched.
#
# REMOVE this once the upstream image ships with httpx. Opt in via:
#   sg content-proxy local up --fix-mitm-httpx
# ─────────────────────────────────────────────────────────────────────────────
FROM diniscruz/mgraph-ai-service-mitmproxy
RUN pip install --no-cache-dir httpx
