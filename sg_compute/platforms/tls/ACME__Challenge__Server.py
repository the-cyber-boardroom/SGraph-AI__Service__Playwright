# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — ACME__Challenge__Server
# A throwaway HTTP server for the ACME http-01 challenge. Let's Encrypt fetches
# http://<ip>/.well-known/acme-challenge/<token>; this serves exactly that one
# path with the key-authorization string, and 404s everything else.
#
# Plain class, not Type_Safe: it wraps a threaded http.server whose handler /
# socket / thread objects have no Type_Safe representation — the same pragmatic
# carve-out the test suite makes when it spins up HTTPServer instances.
# ═══════════════════════════════════════════════════════════════════════════════

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

_CHALLENGES : dict = {}                                  # path -> key-authorization, shared with the handler


class _Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        body = _CHALLENGES.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        payload = body.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):                   # keep cert-init logs clean
        return


class ACME__Challenge__Server:

    def __init__(self, port: int = 80):
        self.port   = port
        self.server = None
        self.thread = None

    def set_challenge(self, path: str, key_authorization: str) -> None:
        _CHALLENGES[path] = key_authorization

    def clear(self) -> None:
        _CHALLENGES.clear()

    def start(self) -> None:
        self.server = HTTPServer(('0.0.0.0', self.port), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self.clear()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        return False
