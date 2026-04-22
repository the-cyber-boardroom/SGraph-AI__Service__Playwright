#!/bin/sh
# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — container entrypoint
#
# 1. Seed /app/current_interceptor.py from the baked default.
# 2. Build the mitmweb command line from env vars (all flags conditional).
# 3. Write /tmp/run_mitmweb.sh — supervisord calls this wrapper so it gets
#    the computed command without needing a dynamic supervisord.conf.
# 4. Exec supervisord.
#
# Proxy modes (mutually exclusive at boot; chosen by env vars):
#   direct   — no AGENT_MITMPROXY__UPSTREAM_URL set
#              mitmweb terminates TLS and forwards directly to the internet.
#   upstream — AGENT_MITMPROXY__UPSTREAM_URL set
#              mitmweb runs --mode upstream:<url>; if UPSTREAM_USER + PASS are
#              also set, --set upstream_auth=<user>:<pass> is added (preemptive
#              auth on every CONNECT — avoids the 407-retry bug).
#
# Downstream auth (--proxyauth):
#   Optional. Only added when AGENT_MITMPROXY__PROXY_AUTH_USER and _PASS are
#   both set. Leave unset when paired with the Playwright service — security
#   comes from Docker network isolation, not HTTP auth on :8080.
# ═══════════════════════════════════════════════════════════════════════════════

set -eu

# ── 1. Seed interceptor ───────────────────────────────────────────────────────

if [ ! -f /app/current_interceptor.py ]; then
    cp /app/agent_mitmproxy/addons/default_interceptor.py /app/current_interceptor.py
fi

# ── 2. Build mitmweb command line ─────────────────────────────────────────────

MITMWEB_CMD="mitmweb"

# Downstream proxy auth — optional; omit when paired with Playwright
if [ -n "${AGENT_MITMPROXY__PROXY_AUTH_USER:-}" ] && [ -n "${AGENT_MITMPROXY__PROXY_AUTH_PASS:-}" ]; then
    MITMWEB_CMD="${MITMWEB_CMD} --proxyauth ${AGENT_MITMPROXY__PROXY_AUTH_USER}:${AGENT_MITMPROXY__PROXY_AUTH_PASS}"
fi

# Upstream forwarding mode — set when traffic must go via an authenticated upstream
if [ -n "${AGENT_MITMPROXY__UPSTREAM_URL:-}" ]; then
    MITMWEB_CMD="${MITMWEB_CMD} --mode upstream:${AGENT_MITMPROXY__UPSTREAM_URL}"
    if [ -n "${AGENT_MITMPROXY__UPSTREAM_USER:-}" ] && [ -n "${AGENT_MITMPROXY__UPSTREAM_PASS:-}" ]; then
        MITMWEB_CMD="${MITMWEB_CMD} --set upstream_auth=${AGENT_MITMPROXY__UPSTREAM_USER}:${AGENT_MITMPROXY__UPSTREAM_PASS}"
    fi
    MITMWEB_CMD="${MITMWEB_CMD} --ssl-insecure"                                  # upstream always presents a forged cert; skip verification
fi

# HTTP/2 on upstream connections — disable to fix InvalidBodyLengthError with some proxies
if [ "${AGENT_MITMPROXY__HTTP2:-true}" = "false" ]; then
    MITMWEB_CMD="${MITMWEB_CMD} --set http2=false"
fi

# Fixed flags (always present)
MITMWEB_CMD="${MITMWEB_CMD} --web-host 127.0.0.1"
MITMWEB_CMD="${MITMWEB_CMD} --web-port 8081"
MITMWEB_CMD="${MITMWEB_CMD} --listen-port 8080"
MITMWEB_CMD="${MITMWEB_CMD} --set block_global=false"
MITMWEB_CMD="${MITMWEB_CMD} --set confdir=/root/.mitmproxy"
MITMWEB_CMD="${MITMWEB_CMD} -s /app/agent_mitmproxy/addons/addon_registry.py"

# ── 3. Write wrapper script ───────────────────────────────────────────────────

printf '#!/bin/sh\nexec %s\n' "${MITMWEB_CMD}" > /tmp/run_mitmweb.sh
chmod +x /tmp/run_mitmweb.sh

# ── 4. Hand off to supervisord ────────────────────────────────────────────────

exec supervisord -c /app/supervisord.conf
