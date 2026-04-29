# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__HTTP__Probe
# Real _Fake_HTTP subclass overrides request(); no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__HTTP__Base                  import Vnc__HTTP__Base
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__HTTP__Probe                 import Vnc__HTTP__Probe


class _Fake_Response:
    def __init__(self, status_code=200, json_body=None, raises=None):
        self.status_code = status_code
        self._json       = json_body if json_body is not None else []
        self._raises     = raises
    def json(self):
        if self._raises:
            raise self._raises
        return self._json


class _Fake_HTTP(Vnc__HTTP__Base):
    def __init__(self, response):
        super().__init__()
        self.calls    = []
        self.response = response
    def request(self, method, url, *, headers=None, data=None, params=None, username='', password=''):
        self.calls.append({'method': method, 'url': url, 'username': username, 'password': password})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _probe(response):
    http  = _Fake_HTTP(response)
    return http, Vnc__HTTP__Probe(http=http)


class test_nginx_ready(TestCase):

    def test__2xx_is_ready(self):
        http, probe = _probe(_Fake_Response(status_code=204))
        assert probe.nginx_ready('https://1.2.3.4', 'operator', 'secret') is True
        assert http.calls[0]['url']      == 'https://1.2.3.4/'
        assert http.calls[0]['username'] == 'operator'

    def test__non_2xx_is_not_ready(self):
        for code in (401, 500):
            _, probe = _probe(_Fake_Response(status_code=code))
            assert probe.nginx_ready('https://1.2.3.4') is False

    def test__network_error_is_not_ready(self):
        _, probe = _probe(ConnectionError('refused'))
        assert probe.nginx_ready('https://1.2.3.4') is False

    def test__strips_trailing_slash_and_normalises(self):
        http, probe = _probe(_Fake_Response())
        probe.nginx_ready('https://1.2.3.4/')
        assert http.calls[0]['url'] == 'https://1.2.3.4/'


class test_mitmweb_ready(TestCase):

    def test__200_is_ready(self):
        http, probe = _probe(_Fake_Response(status_code=200, json_body=[]))
        assert probe.mitmweb_ready('https://1.2.3.4') is True
        assert http.calls[0]['url'] == 'https://1.2.3.4/flows'

    def test__non_200_is_not_ready(self):
        for code in (302, 403, 502):
            _, probe = _probe(_Fake_Response(status_code=code))
            assert probe.mitmweb_ready('https://1.2.3.4') is False

    def test__network_error_is_not_ready(self):
        _, probe = _probe(ConnectionError('refused'))
        assert probe.mitmweb_ready('https://1.2.3.4') is False


class test_flows_listing(TestCase):

    def test__200_returns_parsed_list(self):
        body = [{'id': 'aaa', 'request': {'method': 'GET'}},
                {'id': 'bbb', 'request': {'method': 'POST'}}]
        http, probe = _probe(_Fake_Response(status_code=200, json_body=body))
        out = probe.flows_listing('https://1.2.3.4')
        assert out == body
        assert http.calls[0]['url'] == 'https://1.2.3.4/flows'

    def test__non_200_returns_empty_list(self):
        _, probe = _probe(_Fake_Response(status_code=503))
        assert probe.flows_listing('https://1.2.3.4') == []

    def test__non_json_returns_empty_list(self):
        _, probe = _probe(_Fake_Response(status_code=200, raises=ValueError('not json')))
        assert probe.flows_listing('https://1.2.3.4') == []

    def test__non_array_body_returns_empty_list(self):                              # Defensive: future mitmweb might return {'flows': [...]}
        _, probe = _probe(_Fake_Response(status_code=200, json_body={'flows': []}))
        assert probe.flows_listing('https://1.2.3.4') == []

    def test__network_error_returns_empty_list(self):
        _, probe = _probe(ConnectionError('refused'))
        assert probe.flows_listing('https://1.2.3.4') == []
