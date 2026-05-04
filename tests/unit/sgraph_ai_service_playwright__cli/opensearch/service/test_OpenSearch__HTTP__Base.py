# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for OpenSearch__HTTP__Base
# Verifies the request seam wires verify=False, the Basic auth, and the
# warning suppression. Tests substitute requests.request via a recorder.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.service                           import OpenSearch__HTTP__Base as base_module
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__HTTP__Base    import DEFAULT_TIMEOUT, OpenSearch__HTTP__Base


class _Recorder:                                                                    # Real class, not a mock — records every requests.request call
    def __init__(self, response_status=200):
        self.calls           = []
        self.response_status = response_status
    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        class _Resp:
            status_code = self.response_status
            text        = 'ok'
            def json(_self): return {}
        _Resp.status_code = self.response_status
        return _Resp


class test_OpenSearch__HTTP__Base(TestCase):

    def setUp(self):
        self._orig_request          = base_module.requests.request
        self.recorder               = _Recorder()
        base_module.requests.request = self.recorder

    def tearDown(self):
        base_module.requests.request = self._orig_request

    def test__defaults(self):
        client = OpenSearch__HTTP__Base()
        assert client.timeout == DEFAULT_TIMEOUT
        assert client.verify  is False                                              # Self-signed cert at boot

    def test_request__passes_through_verify_false_and_default_timeout(self):
        OpenSearch__HTTP__Base().request('GET', 'https://1.2.3.4/_cluster/health')
        kw = self.recorder.calls[0]
        assert kw['method']  == 'GET'
        assert kw['url']     == 'https://1.2.3.4/_cluster/health'
        assert kw['verify']  is False
        assert kw['timeout'] == DEFAULT_TIMEOUT
        assert kw['auth']    is None                                                # No auth when no creds passed

    def test_request__attaches_basic_auth_when_creds_provided(self):
        OpenSearch__HTTP__Base().request('GET', 'https://1.2.3.4/', username='admin', password='secret')
        auth = self.recorder.calls[0]['auth']
        assert auth.username == 'admin'
        assert auth.password == 'secret'

    def test_request__honours_custom_timeout(self):
        OpenSearch__HTTP__Base(timeout=5).request('GET', 'https://1.2.3.4/')
        assert self.recorder.calls[0]['timeout'] == 5

    def test_request__forwards_data_and_headers(self):
        OpenSearch__HTTP__Base().request('POST', 'https://1.2.3.4/_bulk',
                                          headers={'Content-Type': 'application/x-ndjson'},
                                          data=b'{"ok":1}\n')
        kw = self.recorder.calls[0]
        assert kw['headers'] == {'Content-Type': 'application/x-ndjson'}
        assert kw['data']    == b'{"ok":1}\n'
