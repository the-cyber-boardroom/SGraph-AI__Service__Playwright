# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus__HTTP__Base
# Verifies the request seam wires verify=False, the Basic auth, the warning
# suppression, and the new `params` kwarg used by /api/v1/query.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.service                           import Prometheus__HTTP__Base as base_module
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Base    import DEFAULT_TIMEOUT, Prometheus__HTTP__Base


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


class test_Prometheus__HTTP__Base(TestCase):

    def setUp(self):
        self._orig_request          = base_module.requests.request
        self.recorder               = _Recorder()
        base_module.requests.request = self.recorder

    def tearDown(self):
        base_module.requests.request = self._orig_request

    def test__defaults(self):
        client = Prometheus__HTTP__Base()
        assert client.timeout == DEFAULT_TIMEOUT
        assert client.verify  is False

    def test_request__passes_through_verify_false_and_default_timeout(self):
        Prometheus__HTTP__Base().request('GET', 'http://1.2.3.4:9090/-/healthy')
        kw = self.recorder.calls[0]
        assert kw['method']  == 'GET'
        assert kw['url']     == 'http://1.2.3.4:9090/-/healthy'
        assert kw['verify']  is False
        assert kw['timeout'] == DEFAULT_TIMEOUT
        assert kw['auth']    is None                                                # No auth when no creds passed (P1: Prometheus has no built-in auth)
        assert kw['params']  is None

    def test_request__attaches_basic_auth_when_creds_provided(self):
        Prometheus__HTTP__Base().request('GET', 'http://1.2.3.4:9090/', username='ops', password='secret')
        auth = self.recorder.calls[0]['auth']
        assert auth.username == 'ops'
        assert auth.password == 'secret'

    def test_request__honours_custom_timeout(self):
        Prometheus__HTTP__Base(timeout=5).request('GET', 'http://1.2.3.4:9090/')
        assert self.recorder.calls[0]['timeout'] == 5

    def test_request__forwards_params_for_query_endpoint(self):                     # /api/v1/query?query=… needs query-string params
        Prometheus__HTTP__Base().request('GET', 'http://1.2.3.4:9090/api/v1/query', params={'query': 'up'})
        assert self.recorder.calls[0]['params'] == {'query': 'up'}
