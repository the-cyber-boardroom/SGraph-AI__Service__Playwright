# ═══════════════════════════════════════════════════════════════════════════════
# sg_edge edge-waker — Routes__Edge_Waker
# Root-mounted (tag='') route class. Diagnostic + control surfaces are explicit
# paths; the catch-all is the CloudFront cold-cold failover entry that serves the
# loading page.
#
#   GET  /__edge__/health      JSON liveness
#   GET  /__edge__/status      JSON {ready, proxies} — polled by the loading page
#   POST /__edge__/reconcile   run the convergent scale check (scheduled/admin)
#   POST /__edge__/idle-check  run the idle-teardown counter step (scheduled)
#   *    /{path:path}          cold-cold: best-effort boot + serve loading page
#
# The catch-all is registered LAST so explicit paths (and FastAPI's /docs,
# /openapi.json) win the match. Routes are thin — all logic is in the injected
# SG_Edge__Fleet__Reconciler (brief: "routes have no logic").
# ═══════════════════════════════════════════════════════════════════════════════

from starlette.requests                         import Request
from starlette.responses                        import HTMLResponse, JSONResponse
from osbot_fast_api.api.routes.Fast_API__Routes import Fast_API__Routes

from sg_compute_specs.sg_edge.lambdas.edge_waker.Loading__Page         import Loading__Page
from sg_compute_specs.sg_edge.lambdas.edge_waker.edge_waker__config    import EDGE_WAKER_VERSION
from sg_compute_specs.sg_edge.service.SG_Edge__Fleet__Reconciler       import SG_Edge__Fleet__Reconciler

ROUTES_PATHS__EDGE_WAKER = ['/__edge__/health', '/__edge__/status',
                            '/__edge__/reconcile', '/__edge__/idle-check',
                            '/{path:path}']


class Routes__Edge_Waker(Fast_API__Routes):
    tag        : str                        = ''                                     # root-mounted (no prefix)
    reconciler : SG_Edge__Fleet__Reconciler                                          # injected via add_routes(...)

    # ── diagnostics ───────────────────────────────────────────────────────────
    def health(self):
        return {'status': 'ok', 'service': 'sg-edge-waker', 'version': EDGE_WAKER_VERSION}
    health.__route_path__ = '/__edge__/health'

    def status(self):                                                                # polled by the loading page
        count = self.reconciler.dns.proxy_count(self.reconciler.parent)
        return {'ready': count > 0, 'proxies': count}
    status.__route_path__ = '/__edge__/status'

    # ── control plane ───────────────────────────────────────────────────────────
    def reconcile(self):                                                             # scheduled scale check / admin trigger
        return self.reconciler.reconcile()
    reconcile.__route_path__ = '/__edge__/reconcile'

    def idle_check(self):                                                            # scheduled idle-teardown step
        return self.reconciler.idle_check()
    idle_check.__route_path__ = '/__edge__/idle-check'

    # ── cold-cold catch-all ───────────────────────────────────────────────────────
    async def cold_cold(self, request: Request, path: str = ''):
        try:
            self.reconciler.ensure_booting()                                         # best-effort; the scheduled reconcile guarantees convergence
        except Exception:                                                            # an unwired/slow launcher must never block the loading page
            pass
        return HTMLResponse(Loading__Page().render(EDGE_WAKER_VERSION),
                            headers={'Cache-Control': 'no-store'})
    cold_cold.__route_path__ = '/{path:path}'

    def setup_routes(self):
        self.add_route_get (self.health)
        self.add_route_get (self.status)
        self.add_route_post(self.reconcile)
        self.add_route_post(self.idle_check)
        self.add_route_any (self.cold_cold, path='/{path:path}')                     # registered LAST — lowest match priority
