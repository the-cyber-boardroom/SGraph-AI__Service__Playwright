# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: TUI render + flow-mapper tests (3.11-safe)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy                 import Enum__Content_Proxy__Proxy
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Flow__Summary     import Schema__Content_Proxy__Flow__Summary
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Stack__Info       import Schema__Content_Proxy__Stack__Info
from sg_compute_specs.content_proxy.service.Content_Proxy__Flow__Mapper              import Content_Proxy__Flow__Mapper
from sg_compute_specs.content_proxy.tui.renders.Content_Proxy__TUI__Status__Render   import status_markup, status_plain
from sg_compute_specs.content_proxy.tui.renders.Content_Proxy__TUI__Traffic__Render  import traffic_markup, traffic_plain


class test_Flow__Mapper(TestCase):

    def test_injected_flow_from_mitmweb_entry(self):
        raw = {'request' : {'method': 'GET', 'host': 'news.site', 'path': '/9',
                            'headers': [['x-proxy-request-count', '42']]},
               'response': {'status_code': 200,
                            'headers': [['x-proxy-action', 'injected'],
                                        ['x-proxy-status', 'fastapi-connected']]}}
        f = Content_Proxy__Flow__Mapper().to_flow_summary(raw, via=Enum__Content_Proxy__Proxy.EXT)
        assert f.action            == Enum__Content_Proxy__Flow__Action.INJECTED
        assert f.via               == Enum__Content_Proxy__Proxy.EXT
        assert f.fastapi_connected is True
        assert f.status_code       == 200
        assert str(f.host)         == 'news.site'
        assert str(f.request_id)   == '42'

    def test_blocked_action_from_dict_headers(self):
        raw = {'request' : {'method': 'GET', 'host': 'bad.site', 'path': '/',
                            'headers': {'x-proxy-action': 'blocked'}},
               'response': {'status_code': 403, 'headers': {}}}
        f = Content_Proxy__Flow__Mapper().to_flow_summary(raw)
        assert f.action == Enum__Content_Proxy__Flow__Action.BLOCKED

    def test_unknown_action_defaults_passed(self):
        raw = {'request': {'method': 'GET', 'host': 'h', 'path': '/'}, 'response': {}}
        f = Content_Proxy__Flow__Mapper().to_flow_summary(raw)
        assert f.action      == Enum__Content_Proxy__Flow__Action.PASSED
        assert f.status_code == 0


def _info(**kw):
    return Schema__Content_Proxy__Stack__Info(**kw)


def _flow(action, via=Enum__Content_Proxy__Proxy.INT, status=200):
    return Schema__Content_Proxy__Flow__Summary(via=via, method='GET', host='h', path='/',
                                                status_code=status, action=action,
                                                fastapi_connected=True)


class test_Status__Render(TestCase):

    def test_markup_shows_all_five_components_and_smoke(self):
        out = status_markup(_info(mitmproxy_ext_ok=True, mitmproxy_int_ok=True,
                                  mitm_service_ok=True, playwright_ok=True, vault_app_ok=False),
                            smoke_ok=True)
        for s in ('mitmproxy-ext', 'mitmproxy-int', 'mitm-service', 'sg-playwright', 'vault-app'):
            assert s in out
        assert '● up'   in out
        assert '● down' in out                                                      # vault-app down
        assert 'PASS'   in out                                                      # smoke

    def test_plain_has_no_markup(self):
        out = status_plain(_info(mitmproxy_ext_ok=True), smoke_ok=False)
        assert '[' not in out
        assert 'mitmproxy-ext  up' in out


class test_Traffic__Render(TestCase):

    def test_markup_lists_flows_and_actions(self):
        out = traffic_markup([_flow(Enum__Content_Proxy__Flow__Action.INJECTED),
                              _flow(Enum__Content_Proxy__Flow__Action.BLOCKED, status=403)])
        assert 'Traffic' in out
        assert 'injected' in out and 'blocked' in out

    def test_markup_empty(self):
        assert 'no flows captured yet' in traffic_markup([])

    def test_plain_has_no_markup(self):
        out = traffic_plain([_flow(Enum__Content_Proxy__Flow__Action.INJECTED)])
        assert '[' not in out and 'injected' in out
