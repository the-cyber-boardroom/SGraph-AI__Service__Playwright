# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish admin — Routes__Admin
# Root-mounted (tag='') route class for the admin surface. HTML pages + login
# flow + the JSON API, all on one class since they share the Admin__Service.
#
#   GET  /                      inventory HTML            (auth-gated by middleware)
#   GET  /login                 login form                (auth-free)
#   POST /login                 set cookie, redirect to / (auth-free)
#   GET  /logout                clear cookie → /login     (auth-gated)
#   GET  /slug/{slug}/          per-slug HTML             (auth-gated)
#   GET  /api/v1/list           JSON inventory            (auth-gated)
#   GET  /api/v1/status         JSON waker-state probe    (auth-FREE — warming pages)
#   GET  /api/v1/eval           JSON 7-step eval          (auth-gated)
#
# Auth is enforced by Admin__Auth__Middleware (cookie/header gate), NOT per
# route — so methods here assume the request already passed the gate (except
# the explicitly auth-free paths the middleware lets through).
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                       import Form
from fastapi.responses                             import HTMLResponse, RedirectResponse, JSONResponse
from osbot_fast_api.api.routes.Fast_API__Routes    import Fast_API__Routes

from sg_compute_specs.vault_publish.lambdas.admin.Admin__Service import Admin__Service
from sg_compute_specs.vault_publish.lambdas.admin.Admin__Pages   import render_login, render_inventory, render_slug
from sg_compute_specs.vault_publish.lambdas.admin.Admin__Auth    import (
    configured_key_name, configured_key_value, _consteq)
from sg_compute_specs.vault_publish.lambdas.admin.admin__config  import admin_zone


ROUTES_PATHS__ADMIN = ['/', '/login', '/logout', '/slug/{slug}/',
                       '/api/v1/list', '/api/v1/status', '/api/v1/eval']


class Routes__Admin(Fast_API__Routes):
    tag           : str           = ''                                               # root-mounted (no prefix)
    admin_service : Admin__Service = None

    # ── HTML pages ──────────────────────────────────────────────────────────
    def index(self) -> HTMLResponse:
        return HTMLResponse(render_inventory(self.admin_service.list_entries(), admin_zone()))
    index.__route_path__ = '/'

    def slug__slug(self, slug: str) -> HTMLResponse:
        status     = self.admin_service.status(slug)
        eval_steps = self.admin_service.eval(slug)
        return HTMLResponse(render_slug(slug, eval_steps, status))
    slug__slug.__route_path__ = '/slug/{slug}/'

    # ── login / logout ──────────────────────────────────────────────────────
    def login(self) -> HTMLResponse:
        return HTMLResponse(render_login())
    login.__route_path__ = '/login'

    def login_submit(self, api_key: str = Form(...)):
        expected = configured_key_value()
        if not expected:
            return HTMLResponse(render_login(flash='Admin auth is not configured on this Lambda.',
                                             flash_kind='error'), status_code=503)
        if not _consteq(api_key, expected):
            return HTMLResponse(render_login(flash='Invalid API key.', flash_kind='error'),
                                status_code=401)
        resp = RedirectResponse(url='/', status_code=302)
        resp.set_cookie(key=configured_key_name(), value=api_key, domain='.' + admin_zone(),
                        path='/', secure=True, httponly=False, samesite='lax',
                        max_age=30 * 24 * 3600)
        return resp
    login_submit.__route_path__ = '/login'

    def logout(self):
        resp = RedirectResponse(url='/login', status_code=302)
        resp.delete_cookie(configured_key_name(), domain='.' + admin_zone(), path='/')
        return resp
    logout.__route_path__ = '/logout'

    # ── JSON API ──────────────────────────────────────────────────────────────
    def api_v1_list(self) -> dict:
        return {'entries': self.admin_service.list_entries(), 'zone': admin_zone()}
    api_v1_list.__route_path__ = '/api/v1/list'

    def api_v1_status(self, slug: str = ''):
        # Public (auth-free) probe — used by warming pages cross-origin.
        if not slug:
            return JSONResponse({'error': 'slug query param required'}, status_code=400)
        return JSONResponse(self.admin_service.waker_state(slug))
    api_v1_status.__route_path__ = '/api/v1/status'

    def api_v1_eval(self, slug: str = ''):
        if not slug:
            return JSONResponse({'error': 'slug query param required'}, status_code=400)
        return JSONResponse({'slug': slug, 'steps': self.admin_service.eval(slug)})
    api_v1_eval.__route_path__ = '/api/v1/eval'

    def setup_routes(self):
        self.add_route_get (self.index)
        self.add_route_get (self.slug__slug)
        self.add_route_get (self.login)
        self.add_route_post(self.login_submit)
        self.add_route_get (self.logout)
        self.add_route_get (self.api_v1_list)
        self.add_route_get (self.api_v1_status)
        self.add_route_get (self.api_v1_eval)
