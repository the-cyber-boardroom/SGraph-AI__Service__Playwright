# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Echo__Server (real loopback HTTP — no AWS, no mocks)
# Starts the stdlib server on an ephemeral port in a thread, hits it, asserts the
# echo + the /__hits introspection.
# ═══════════════════════════════════════════════════════════════════════════════

import threading
from http.server import ThreadingHTTPServer

import requests

import sgraph_ai_service_playwright__cli.sentinel.traffic.echo.Echo__Server as echo_mod
from sgraph_ai_service_playwright__cli.sentinel.traffic.echo.Echo__Server import _Echo_Handler


class _Server:
    def __enter__(self):
        echo_mod._HITS.clear()
        self.httpd  = ThreadingHTTPServer(('127.0.0.1', 0), _Echo_Handler)
        self.port   = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    @property
    def base(self):
        return f'http://127.0.0.1:{self.port}'

    def __exit__(self, *_):
        self.httpd.shutdown()


class TestEcho:
    def test_get_echoes_request_as_json(self):
        with _Server() as s:
            resp = requests.get(s.base + '/etc/passwd', headers={'X-Forwarded-For': '185.10.10.10'}, timeout=5)
            assert resp.status_code == 200
            body = resp.json()
            assert body['path'] == '/etc/passwd'
            assert body['source_ip'] == '185.10.10.10'                               # XFF honoured

    def test_html_format(self):
        with _Server() as s:
            resp = requests.get(s.base + '/?format=html', timeout=5)
            assert 'text/html' in resp.headers['Content-Type'] and '<table' in resp.text

    def test_hits_introspection_records_what_reached_origin(self):
        with _Server() as s:
            requests.get(s.base + '/a', timeout=5)
            requests.get(s.base + '/b', timeout=5)
            hits = requests.get(s.base + '/__hits', timeout=5).json()
            assert hits['count'] == 2
            assert {h['path'] for h in hits['hits']} == {'/a', '/b'}
