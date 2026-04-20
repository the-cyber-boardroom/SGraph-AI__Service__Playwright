# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Environment Variable Names
#
# Every env var is read via get_env(ENV_VAR__NAME) — never os.environ.get().
# Two prefixes:
#   • AGENT_MITMPROXY__ — service-specific vars (proxy auth, mitmweb wiring, cert path)
#   • FAST_API__AUTH__ — reuses the Serverless__Fast_API API-key middleware names
# ═══════════════════════════════════════════════════════════════════════════════

# ── Proxy auth (mitmweb --proxyauth) ─────────────────────────────────────────
ENV_VAR__PROXY_AUTH_USER          = 'AGENT_MITMPROXY__PROXY_AUTH_USER'
ENV_VAR__PROXY_AUTH_PASS          = 'AGENT_MITMPROXY__PROXY_AUTH_PASS'

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
