# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Default filesystem paths (inside the container)
#
# mitmweb writes the CA PEM to PATH__CA_CERT_PEM on first start — the admin API
# reads it on demand for /ca/cert and /ca/info. entrypoint.sh seeds
# PATH__CURRENT_INTERCEPTOR from the baked default_interceptor.py so
# /config/interceptor has something to return.
#
# Both are overridable via env_vars.ENV_VAR__CA_CERT_PATH / _INTERCEPTOR_PATH.
# ═══════════════════════════════════════════════════════════════════════════════

PATH__CA_CERT_PEM          = '/root/.mitmproxy/mitmproxy-ca-cert.pem'
PATH__CURRENT_INTERCEPTOR  = '/app/current_interceptor.py'
