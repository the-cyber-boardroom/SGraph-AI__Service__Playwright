# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for OpenSearch__HTTP__Probe
# Real Fake_HTTP subclass overrides request(); no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__HTTP__Base    import OpenSearch__HTTP__Base
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__HTTP__Probe   import OpenSearch__HTTP__Probe


class _Fake_Response:
    def __init__(self, status_code=200, json_body=None, raises=None):
        self.status_code = status_code
        self._json       = json_body if json_body is not None else {}
        self._raises     = raises
    def json(self):
        if self._raises:
            raise self._raises
        return self._json


class _Fake_HTTP(OpenSearch__HTTP__Base):                                            # Real subclass, no mocks
    def __init__(self, response):
        super().__init__()
        self.calls    = []
        self.response = response
    def request(self, method, url, *, headers=None, data=None, username='', password=''):
        self.calls.append({'method': method, 'url': url, 'username': username, 'password': password})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class test_cluster_health(TestCase):

    def _probe_with(self, response):
        http  = _Fake_HTTP(response)
        probe = OpenSearch__HTTP__Probe(http=http)
        return http, probe

    def test__200_returns_parsed_body(self):
        body         = {'cluster_name': 'sg-os', 'status': 'green', 'number_of_nodes': 1, 'active_shards': 5}
        http, probe  = self._probe_with(_Fake_Response(status_code=200, json_body=body))
        out          = probe.cluster_health('https://1.2.3.4', 'admin', 'secret')
        assert out == body
        assert http.calls[0]['method']   == 'GET'
        assert http.calls[0]['url']      == 'https://1.2.3.4/_cluster/health'
        assert http.calls[0]['username'] == 'admin'
        assert http.calls[0]['password'] == 'secret'

    def test__non_200_returns_empty_dict(self):
        _, probe = self._probe_with(_Fake_Response(status_code=503))
        assert probe.cluster_health('https://1.2.3.4') == {}

    def test__network_error_returns_empty_dict(self):                                # Connection refused / DNS / TLS — caller maps to '-1' sentinels in Schema__OS__Health
        _, probe = self._probe_with(ConnectionError('refused'))
        assert probe.cluster_health('https://1.2.3.4') == {}

    def test__non_json_body_returns_empty_dict(self):                                # Defensive: nginx 502 occasionally returns HTML
        _, probe = self._probe_with(_Fake_Response(status_code=200, raises=ValueError('not json')))
        assert probe.cluster_health('https://1.2.3.4') == {}

    def test__strips_trailing_slash_on_base_url(self):                               # URL hygiene — caller may pass either form
        http, probe = self._probe_with(_Fake_Response())
        probe.cluster_health('https://1.2.3.4/')
        assert http.calls[0]['url'] == 'https://1.2.3.4/_cluster/health'             # No '//' in the path


class test_dashboards_ready(TestCase):

    def _probe_with(self, response):
        http  = _Fake_HTTP(response)
        probe = OpenSearch__HTTP__Probe(http=http)
        return http, probe

    def test__2xx_is_ready(self):
        for code in (200, 201, 204, 299):
            _, probe = self._probe_with(_Fake_Response(status_code=code))
            assert probe.dashboards_ready('https://1.2.3.4') is True

    def test__non_2xx_is_not_ready(self):
        for code in (300, 401, 403, 500, 502):
            _, probe = self._probe_with(_Fake_Response(status_code=code))
            assert probe.dashboards_ready('https://1.2.3.4') is False

    def test__network_error_is_not_ready(self):
        _, probe = self._probe_with(ConnectionError('refused'))
        assert probe.dashboards_ready('https://1.2.3.4') is False

    def test__forwards_basic_auth(self):
        http, probe = self._probe_with(_Fake_Response())
        probe.dashboards_ready('https://1.2.3.4', 'admin', 'secret')
        assert http.calls[0]['username'] == 'admin'
        assert http.calls[0]['password'] == 'secret'
