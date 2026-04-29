# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__HTTP__Base
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service                                  import Vnc__HTTP__Base as base_module
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__HTTP__Base                  import DEFAULT_TIMEOUT, Vnc__HTTP__Base


class _Recorder:
    def __init__(self, response_status=200):
        self.calls           = []
        self.response_status = response_status
    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        class _Resp:
            status_code = self.response_status
        _Resp.status_code = self.response_status
        return _Resp


class test_Vnc__HTTP__Base(TestCase):

    def setUp(self):
        self._orig_request          = base_module.requests.request
        self.recorder               = _Recorder()
        base_module.requests.request = self.recorder

    def tearDown(self):
        base_module.requests.request = self._orig_request

    def test__defaults(self):
        client = Vnc__HTTP__Base()
        assert client.timeout == DEFAULT_TIMEOUT
        assert client.verify  is False                                              # nginx self-signed cert at boot

    def test_request__passes_through_verify_false(self):
        Vnc__HTTP__Base().request('GET', 'https://1.2.3.4/')
        kw = self.recorder.calls[0]
        assert kw['method']  == 'GET'
        assert kw['url']     == 'https://1.2.3.4/'
        assert kw['verify']  is False
        assert kw['timeout'] == DEFAULT_TIMEOUT

    def test_request__attaches_basic_auth_when_creds_provided(self):
        Vnc__HTTP__Base().request('GET', 'https://1.2.3.4/', username='operator', password='secret')
        auth = self.recorder.calls[0]['auth']
        assert auth.username == 'operator'
        assert auth.password == 'secret'
