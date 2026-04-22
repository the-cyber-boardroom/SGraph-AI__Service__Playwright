# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Environment Variable Names
#
# Every env var is read via get_env(ENV_VAR__NAME) — never os.environ.get().
# Two prefixes:
#   • AGENT_MITMPROXY__ — service-specific vars (proxy auth, mitmweb wiring, cert path)
#   • FAST_API__AUTH__ — reuses the Serverless__Fast_API API-key middleware names
# ═══════════════════════════════════════════════════════════════════════════════

# ── Downstream proxy auth (mitmweb --proxyauth) ───────────────────────────────
# Optional — omit when paired with Playwright; security comes from Docker network
# isolation. Set only when running the sidecar standalone with client auth needed.
ENV_VAR__PROXY_AUTH_USER          = 'AGENT_MITMPROXY__PROXY_AUTH_USER'
ENV_VAR__PROXY_AUTH_PASS          = 'AGENT_MITMPROXY__PROXY_AUTH_PASS'

# ── Upstream forwarding mode (mitmweb --mode upstream) ────────────────────────
# When UPSTREAM_URL is set the sidecar forwards all traffic through an
# authenticated upstream proxy (mitmweb --mode upstream:<url>).
# UPSTREAM_USER + UPSTREAM_PASS are optional even in upstream mode
# (for open upstream proxies). Auth is preemptive — avoids the 407-retry
# failure that breaks Playwright browsers against authenticated proxies directly.
ENV_VAR__UPSTREAM_URL             = 'AGENT_MITMPROXY__UPSTREAM_URL'
ENV_VAR__UPSTREAM_USER            = 'AGENT_MITMPROXY__UPSTREAM_USER'
ENV_VAR__UPSTREAM_PASS            = 'AGENT_MITMPROXY__UPSTREAM_PASS'
ENV_VAR__HTTP2                    = 'AGENT_MITMPROXY__HTTP2'                    # 'false' → --set http2=false; fixes InvalidBodyLengthError on some upstream proxies

# ── Filesystem wiring ────────────────────────────────────────────────────────
ENV_VAR__CA_CERT_PATH             = 'AGENT_MITMPROXY__CA_CERT_PATH'             # Default /root/.mitmproxy/mitmproxy-ca-cert.pem (written by mitmweb on first start)
ENV_VAR__INTERCEPTOR_PATH         = 'AGENT_MITMPROXY__INTERCEPTOR_PATH'         # Default /app/current_interceptor.py (seeded by entrypoint.sh)

# ── mitmweb + admin API wiring ───────────────────────────────────────────────
ENV_VAR__MITMWEB_HOST             = 'AGENT_MITMPROXY__MITMWEB_HOST'             # Default 127.0.0.1 — NOT exposed on SG
ENV_VAR__MITMWEB_PORT             = 'AGENT_MITMPROXY__MITMWEB_PORT'             # Default 8081
ENV_VAR__ADMIN_API_PORT           = 'AGENT_MITMPROXY__ADMIN_API_PORT'           # Default 8000

# ── API-key middleware (Serverless__Fast_API convention — shared with Playwright) ─
ENV_VAR__API_KEY_NAME             = 'FAST_API__AUTH__API_KEY__NAME'
ENV_VAR__API_KEY_VALUE            = 'FAST_API__AUTH__API_KEY__VALUE'
