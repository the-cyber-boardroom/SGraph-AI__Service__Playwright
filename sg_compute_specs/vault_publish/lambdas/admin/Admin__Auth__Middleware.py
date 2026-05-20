# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish admin — Admin__Auth__Middleware
# Cookie/header API-key gate for the admin surface. Unlike the control plane's
# Middleware__Check_API_Key (which 401s), this redirects unauthenticated browser
# requests to /login so the operator gets the login form.
#
# Auth-free paths (no key required):
#   /login              GET form + POST submit
#   /api/v1/status      public probe (warming pages poll it cross-origin)
#   /docs /openapi.json swagger (so the API surface is browsable)
# Everything else: cookie OR header must match the configured key, else 302
# → /login. Fail-closed when the key env var is unset.
# ═══════════════════════════════════════════════════════════════════════════════

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses       import RedirectResponse, HTMLResponse

from sg_compute_specs.vault_publish.lambdas.admin.Admin__Auth  import Admin__Auth, is_configured
from sg_compute_specs.vault_publish.lambdas.admin.Admin__Pages import render_login

_AUTH_FREE_PREFIXES = ('/login', '/api/v1/status', '/docs', '/redoc',
                       '/openapi.json', '/static-docs')


class Admin__Auth__Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if any(path == p or path.startswith(p) for p in _AUTH_FREE_PREFIXES):
            return await call_next(request)
        if not is_configured():
            return HTMLResponse(render_login(
                flash      = 'Admin auth is not configured on this Lambda. Set '
                             'SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE on the Lambda env '
                             'and re-deploy — see `sg vp setup admin-lambda status`.',
                flash_kind = 'error'), status_code=503)
        if not Admin__Auth().check(headers=dict(request.headers), cookies=dict(request.cookies)):
            return RedirectResponse(url='/login', status_code=302)
        return await call_next(request)
