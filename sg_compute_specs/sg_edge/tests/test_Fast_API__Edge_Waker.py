# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: tests for Fast_API__Edge_Waker
# Exercises the Edge Waker FastAPI surface via Starlette's TestClient with an
# injected reconciler (in-memory DNS + fake launcher; no mocks).
#
# The osbot fast-api serverless stack requires Python 3.12; this suite skips
# cleanly when the stack is unavailable (same gating pattern as the Chromium
# integration tests) and runs in CI where 3.12 + the deps are present.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase, skipUnless

try:
    import starlette                                                                 # noqa: F401  — availability probe
    import osbot_fast_api_serverless                                                 # noqa: F401
    _HAS_FASTAPI = True
except Exception:
    _HAS_FASTAPI = False

from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__Proxy     import Schema__SG_Edge__Proxy
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper       import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.service.SG_Edge__Fleet__Reconciler import SG_Edge__Fleet__Reconciler

PARENT = 'cv.sgraph.ai'


@skipUnless(_HAS_FASTAPI, 'osbot fast-api serverless stack (py3.12) not available in this environment')
class test_Fast_API__Edge_Waker(TestCase):

    def setUp(self):
        from starlette.testclient                                              import TestClient
        from sg_compute_specs.sg_edge.lambdas.edge_waker.Fast_API__Edge_Waker  import Fast_API__Edge_Waker

        self.r53 = Route53__AWS__Client__In_Memory()
        self.r53.seed_zone(PARENT)
        self.dns = SG_Edge__DNS__Helper(route53=self.r53)
        self._n  = [0]

        def _launch():
            self._n[0] += 1
            return Schema__SG_Edge__Proxy(instance_id=f'i-{self._n[0]:017x}', ip=f'10.0.0.{self._n[0]}')

        self.reconciler = SG_Edge__Fleet__Reconciler(dns         = self.dns          ,
                                                     parent      = PARENT            ,
                                                     _launcher   = _launch           ,
                                                     _terminator = lambda ip: None   ,
                                                     _now        = lambda: 1000      )
        self.app_obj = Fast_API__Edge_Waker(reconciler=self.reconciler)
        self.app_obj.setup()
        self.client  = TestClient(self.app_obj.app())

    def test_route_set_matches_documented_paths(self):
        from sg_compute_specs.sg_edge.lambdas.edge_waker.routes.Routes__Edge_Waker import ROUTES_PATHS__EDGE_WAKER
        registered = {getattr(r, 'path', '') for r in self.app_obj.app().routes}
        for path in ROUTES_PATHS__EDGE_WAKER:
            assert path in registered, f'route {path} not registered'

    def test_health(self):
        r = self.client.get('/__edge__/health')
        assert r.status_code == 200
        assert r.json()['status']  == 'ok'
        assert r.json()['service'] == 'sg-edge-waker'

    def test_status__reflects_fleet(self):
        assert self.client.get('/__edge__/status').json() == {'ready': False, 'proxies': 0}
        self.reconciler.ensure_booting()
        assert self.client.get('/__edge__/status').json() == {'ready': True, 'proxies': 1}

    def test_reconcile_endpoint(self):
        r = self.client.post('/__edge__/reconcile')
        assert r.status_code == 200
        assert 'target' in r.json()

    def test_idle_check_endpoint(self):
        r = self.client.post('/__edge__/idle-check')
        assert r.status_code == 200
        assert r.json()['action'] in ('reset', 'increment', 'teardown')

    def test_cold_cold_serves_loading_page_and_boots(self):
        r = self.client.get('/alice')
        assert r.status_code == 200
        assert 'Spinning up' in r.text
        assert self.dns.proxy_count(PARENT) == 1                                     # ensure_booting fired on the catch-all
