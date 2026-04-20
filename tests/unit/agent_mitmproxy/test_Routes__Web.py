# ═══════════════════════════════════════════════════════════════════════════════
# Tests — agent_mitmproxy/fast_api/routes/Routes__Web.py
#
# Spins up a lightweight local HTTPServer on a free port, points MITMWEB_HOST/
# MITMWEB_PORT at it, and asserts the admin API's /web/** catch-all forwards
# requests through and strips the X-API-Key header from the upstream call.
# No mocking — real sockets end-to-end (per CLAUDE.md testing rules).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import socket
import threading
from http.server                                                                     import BaseHTTPRequestHandler, HTTPServer
from unittest                                                                        import TestCase

from fastapi.testclient                                                              import TestClient

from agent_mitmproxy.consts                                                          import env_vars
from agent_mitmproxy.fast_api.Fast_API__Agent_Mitmproxy                              import Fast_API__Agent_Mitmproxy


API_KEY_NAME          = 'X-API-Key'
API_KEY_VALUE         = 'test-key-web'
RECEIVED_HEADERS      = []                                                           # Populated by the fake upstream


class _FakeMitmweb(BaseHTTPRequestHandler):

    def do_GET(self):
        RECEIVED_HEADERS.append(dict(self.headers.items()))
        if self.path == '/':
            body = b'<html>mitmweb-home</html>'
        elif self.path.startswith('/static/app.js'):
            body = b'// javascript'
        else:
            body = b'notfound'
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):                                             # Silence the test output
        return


def _find_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class test_Routes__Web(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.port   = _find_free_port()
        cls.server = HTTPServer(('127.0.0.1', cls.port), _FakeMitmweb)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

        os.environ[env_vars.ENV_VAR__API_KEY_NAME ] = API_KEY_NAME
        os.environ[env_vars.ENV_VAR__API_KEY_VALUE] = API_KEY_VALUE
        os.environ[env_vars.ENV_VAR__MITMWEB_HOST ] = '127.0.0.1'
        os.environ[env_vars.ENV_VAR__MITMWEB_PORT ] = str(cls.port)

        cls.client = TestClient(Fast_API__Agent_Mitmproxy().setup().app())

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        os.environ.pop(env_vars.ENV_VAR__API_KEY_NAME , None)
        os.environ.pop(env_vars.ENV_VAR__API_KEY_VALUE, None)
        os.environ.pop(env_vars.ENV_VAR__MITMWEB_HOST , None)
        os.environ.pop(env_vars.ENV_VAR__MITMWEB_PORT , None)

    def setUp(self):
        RECEIVED_HEADERS.clear()

    def _headers(self) -> dict:
        return {API_KEY_NAME: API_KEY_VALUE}

    def test__index_forwards_and_strips_api_key(self):
        response = self.client.get('/web/', headers=self._headers())
        assert response.status_code == 200
        assert b'mitmweb-home' in response.content

        assert len(RECEIVED_HEADERS) == 1                                             # Upstream was called once
        upstream_headers = {k.lower(): v for k, v in RECEIVED_HEADERS[0].items()}
        assert API_KEY_NAME.lower() not in upstream_headers                           # X-API-Key must not leak downstream

    def test__subpath_forwards(self):
        response = self.client.get('/web/static/app.js', headers=self._headers())
        assert response.status_code == 200
        assert b'javascript' in response.content

    def test__requires_api_key(self):
        response = self.client.get('/web/', headers={})                               # No auth
        assert response.status_code == 401
