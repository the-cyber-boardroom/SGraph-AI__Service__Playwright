# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Echo__Server
# The `httpget` echo server: a dependency-free stdlib HTTP server that echoes each
# request back (JSON by default, HTML on Accept: text/html or ?format=html) and keeps
# a capped in-memory log of what hit it (GET /__hits). It is the origin you point a
# SG/Sentinel distribution at — inspecting /__hits shows exactly which traffic the
# edge let through. Runs anywhere Python runs (local / docker / EC2); the Lambda
# variant reuses Echo__Payload via echo/lambda_handler.py.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:                                                                                 # absolute in-repo; sibling fallback when shipped standalone (docker/EC2)
    from sgraph_ai_service_playwright__cli.sentinel.traffic.echo.Echo__Payload import echo_payload, render_html, wants_html
except ImportError:                                                                  # pragma: no cover
    from Echo__Payload import echo_payload, render_html, wants_html

_HITS    : list = []                                                                 # capped in-memory request log
_HITS_MAX = 1000


def _record(payload: dict) -> None:
    _HITS.append(payload)
    if len(_HITS) > _HITS_MAX:
        del _HITS[0:len(_HITS) - _HITS_MAX]


class _Echo_Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_args):                                                   # silence default stderr logging
        pass

    def _client_ip(self) -> str:
        xff = self.headers.get('X-Forwarded-For', '')                                # honour XFF so a generator can spoof source IPs
        return xff.split(',')[0].strip() if xff else self.client_address[0]

    def _handle(self):
        path, _, qs = self.path.partition('?')
        if path == '/__hits':                                                        # introspection: what reached origin
            body = json.dumps({'count': len(_HITS), 'hits': _HITS}, indent=2).encode('utf-8')
            self._send(200, body, 'application/json'); return
        if path == '/__reset':
            _HITS.clear(); self._send(200, b'{"reset":true}', 'application/json'); return

        length  = int(self.headers.get('Content-Length', 0) or 0)
        body    = self.rfile.read(length).decode('utf-8', 'replace') if length else ''
        payload = echo_payload(self.command, path, qs, dict(self.headers), self._client_ip(), body, seq=len(_HITS) + 1)
        _record(payload)
        if wants_html(dict(self.headers), qs):
            self._send(200, render_html(payload).encode('utf-8'), 'text/html')
        else:
            self._send(200, json.dumps(payload, indent=2).encode('utf-8'), 'application/json')

    def _send(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = do_PATCH = _handle


def serve(host: str = '0.0.0.0', port: int = 8080) -> None:
    httpd = ThreadingHTTPServer((host, port), _Echo_Handler)
    print(f'sg-sentinel httpget echo server on http://{host}:{port}  (GET /__hits to see what reached origin)')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
