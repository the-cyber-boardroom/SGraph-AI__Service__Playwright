# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus__HTTP__Probe
# Real _Fake_HTTP subclass overrides request(); no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Base    import Prometheus__HTTP__Base
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Probe   import Prometheus__HTTP__Probe


class _Fake_Response:
    def __init__(self, status_code=200, json_body=None, raises=None):
        self.status_code = status_code
        self._json       = json_body if json_body is not None else {}
        self._raises     = raises
    def json(self):
        if self._raises:
            raise self._raises
        return self._json


class _Fake_HTTP(Prometheus__HTTP__Base):                                            # Real subclass, no mocks
    def __init__(self, response):
        super().__init__()
        self.calls    = []
        self.response = response
    def request(self, method, url, *, headers=None, data=None, params=None, username='', password=''):
        self.calls.append({'method': method, 'url': url, 'params': params, 'username': username, 'password': password})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class test_prometheus_ready(TestCase):

    def _probe_with(self, response):
        http  = _Fake_HTTP(response)
        probe = Prometheus__HTTP__Probe(http=http)
        return http, probe

    def test__2xx_is_ready(self):
        for code in (200, 201, 204, 299):
            http, probe = self._probe_with(_Fake_Response(status_code=code))
            assert probe.prometheus_ready('http://1.2.3.4:9090') is True
        assert http.calls[-1]['url'] == 'http://1.2.3.4:9090/-/healthy'

    def test__non_2xx_is_not_ready(self):
        for code in (300, 401, 403, 500, 502):
            _, probe = self._probe_with(_Fake_Response(status_code=code))
            assert probe.prometheus_ready('http://1.2.3.4:9090') is False

    def test__network_error_is_not_ready(self):
        _, probe = self._probe_with(ConnectionError('refused'))
        assert probe.prometheus_ready('http://1.2.3.4:9090') is False

    def test__strips_trailing_slash_on_base_url(self):
        http, probe = self._probe_with(_Fake_Response())
        probe.prometheus_ready('http://1.2.3.4:9090/')
        assert http.calls[0]['url'] == 'http://1.2.3.4:9090/-/healthy'              # No '//' in the path


class test_targets_status(TestCase):

    def _probe_with(self, response):
        http  = _Fake_HTTP(response)
        probe = Prometheus__HTTP__Probe(http=http)
        return http, probe

    def test__200_returns_parsed_body(self):
        body         = {'status': 'success',
                        'data'  : {'activeTargets': [{'health': 'up'}, {'health': 'down'}],
                                   'droppedTargets': []}}
        http, probe  = self._probe_with(_Fake_Response(status_code=200, json_body=body))
        out          = probe.targets_status('http://1.2.3.4:9090')
        assert out == body
        assert http.calls[0]['method']   == 'GET'
        assert http.calls[0]['url']      == 'http://1.2.3.4:9090/api/v1/targets'

    def test__non_200_returns_empty_dict(self):
        _, probe = self._probe_with(_Fake_Response(status_code=503))
        assert probe.targets_status('http://1.2.3.4:9090') == {}

    def test__network_error_returns_empty_dict(self):
        _, probe = self._probe_with(ConnectionError('refused'))
        assert probe.targets_status('http://1.2.3.4:9090') == {}

    def test__non_json_body_returns_empty_dict(self):
        _, probe = self._probe_with(_Fake_Response(status_code=200, raises=ValueError('not json')))
        assert probe.targets_status('http://1.2.3.4:9090') == {}


class test_query(TestCase):

    def _probe_with(self, response):
        http  = _Fake_HTTP(response)
        probe = Prometheus__HTTP__Probe(http=http)
        return http, probe

    def test__forwards_query_param(self):
        body         = {'status': 'success', 'data': {'resultType': 'vector', 'result': []}}
        http, probe  = self._probe_with(_Fake_Response(status_code=200, json_body=body))
        out          = probe.query('http://1.2.3.4:9090', 'up{job="playwright"}')
        assert out == body
        assert http.calls[0]['url']    == 'http://1.2.3.4:9090/api/v1/query'
        assert http.calls[0]['params'] == {'query': 'up{job="playwright"}'}

    def test__non_200_returns_empty_dict(self):
        _, probe = self._probe_with(_Fake_Response(status_code=400))
        assert probe.query('http://1.2.3.4:9090', 'bad{') == {}

    def test__network_error_returns_empty_dict(self):
        _, probe = self._probe_with(ConnectionError('refused'))
        assert probe.query('http://1.2.3.4:9090', 'up') == {}
