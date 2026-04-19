# ═══════════════════════════════════════════════════════════════════════════════
# Tests — agent_mitmproxy/addons/audit_log_addon.py
#
# Captures sys.stdout, exercises response() on a fake flow, asserts one JSON
# line with the expected keys lands on stdout. Fluent-bit tails docker logs
# and filters for `^{` — the format must stay JSON-per-line with no prefix.
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import io
import json
import sys
import time
from types                                                                           import SimpleNamespace
from unittest                                                                        import TestCase

from agent_mitmproxy.addons.audit_log_addon                                          import Audit_Log, addons
from agent_mitmproxy.addons.default_interceptor                                      import METADATA__REQUEST_ID


def _make_flow(proxy_user: str = 'agent-user') -> SimpleNamespace:
    auth_value = 'Basic ' + base64.b64encode(f'{proxy_user}:secret'.encode()).decode()
    return SimpleNamespace(
        metadata    = {METADATA__REQUEST_ID: 'abc123def456'},
        client_conn = SimpleNamespace(peername=('1.2.3.4', 54321)),
        request     = SimpleNamespace(method   = 'GET'                                  ,
                                      scheme   = 'https'                                ,
                                      host     = 'api.example.com'                      ,
                                      path     = '/v1/foo'                              ,
                                      headers  = {'Proxy-Authorization': auth_value}    ,
                                      content  = b'x' * 10                              ,
                                      timestamp_start = time.time() - 0.100             ),
        response    = SimpleNamespace(status_code     = 200                             ,
                                      content         = b'y' * 20                       ,
                                      timestamp_end   = time.time()                     ))


class test_Audit_Log(TestCase):

    def _capture_stdout(self, addon: Audit_Log, flow) -> str:
        buf = io.StringIO()
        original = sys.stdout
        sys.stdout = buf
        try:
            addon.response(flow)
        finally:
            sys.stdout = original
        return buf.getvalue()

    def test__emits_one_json_line_with_expected_keys(self):
        output = self._capture_stdout(Audit_Log(), _make_flow())

        lines = output.strip().split('\n')
        assert len(lines) == 1
        entry = json.loads(lines[0])

        assert entry['flow_id'       ] == 'abc123def456'
        assert entry['method'        ] == 'GET'
        assert entry['scheme'        ] == 'https'
        assert entry['host'          ] == 'api.example.com'
        assert entry['path'          ] == '/v1/foo'
        assert entry['status'        ] == 200
        assert entry['bytes_request' ] == 10
        assert entry['bytes_response'] == 20
        assert entry['client_addr'   ] == '1.2.3.4'
        assert entry['proxy_user'    ] == 'agent-user'
        assert entry['elapsed_ms'    ] >= 90                                             # ~100ms with CI slack
        assert entry['ts'            ].endswith('+00:00')                                # UTC isoformat

    def test__malformed_auth_header_leaves_proxy_user_none(self):
        flow = _make_flow()
        flow.request.headers['Proxy-Authorization'] = 'Basic !!!not-base64!!!'
        output = self._capture_stdout(Audit_Log(), flow)
        entry  = json.loads(output.strip())
        assert entry['proxy_user'] in (None, '')                                         # Graceful degrade — we don't want audit log to crash the proxy

    def test__addons_export(self):
        assert len(addons) == 1
        assert isinstance(addons[0], Audit_Log)
