# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Routes__Vnc__Flows
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional
from unittest                                                                       import TestCase

from osbot_fast_api.api.Fast_API                                                    import Fast_API

from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Mitm__Flow__Summary import List__Schema__Vnc__Mitm__Flow__Summary
from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Flows       import Routes__Vnc__Flows
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Mitm__Flow__Summary import Schema__Vnc__Mitm__Flow__Summary
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info         import Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                     import Vnc__Service


def _info():
    return Schema__Vnc__Stack__Info(stack_name='vnc-prod', instance_id='i-0123456789abcdef0',
                                      public_ip='5.6.7.8', mitmweb_url='https://5.6.7.8/mitmweb/')


class _Fake_Service(Vnc__Service):
    def __init__(self, hit: bool = True, flows=None):
        super().__init__()
        self.hit              = hit
        self.scripted_flows   = flows or []
        self.last_flows_args  : Optional[tuple] = None

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Vnc__Stack__Info]:
        return _info() if self.hit else None

    def flows(self, region: str, stack_name: str, username: str = '', password: str = '') -> List__Schema__Vnc__Mitm__Flow__Summary:
        self.last_flows_args = (region, stack_name, username, password)
        out = List__Schema__Vnc__Mitm__Flow__Summary()
        for f in self.scripted_flows:
            out.append(f)
        return out


def _client(service: _Fake_Service):
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Vnc__Flows, service=service)
    return app.client()


class test_Routes__Vnc__Flows(TestCase):

    def test_flows__miss_returns_404(self):
        c    = _client(_Fake_Service(hit=False))
        resp = c.get('/vnc/stack/no-such/flows')
        assert resp.status_code == 404
        assert 'no vnc stack' in resp.json()['detail']

    def test_flows__hit_empty(self):
        c    = _client(_Fake_Service(hit=True, flows=[]))
        resp = c.get('/vnc/stack/vnc-prod/flows')
        assert resp.status_code == 200
        assert resp.json()      == {'flows': []}

    def test_flows__hit_with_summaries(self):
        flows = [Schema__Vnc__Mitm__Flow__Summary(flow_id='aaa', method='GET',  url='https://example.com/a', status_code=200),
                 Schema__Vnc__Mitm__Flow__Summary(flow_id='bbb', method='POST', url='https://example.com/b')]
        c     = _client(_Fake_Service(hit=True, flows=flows))
        resp  = c.get('/vnc/stack/vnc-prod/flows')
        assert resp.status_code == 200
        body  = resp.json()
        assert len(body['flows'])             == 2
        assert body['flows'][0]['method']     == 'GET'
        assert body['flows'][0]['status_code'] == 200
        assert body['flows'][1]['method']     == 'POST'

    def test_flows__forwards_creds(self):
        svc  = _Fake_Service(hit=True)
        c    = _client(svc)
        c.get('/vnc/stack/vnc-prod/flows?username=operator&password=secret')
        assert svc.last_flows_args[2] == 'operator'
        assert svc.last_flows_args[3] == 'secret'
