# ═══════════════════════════════════════════════════════════════════════════════
# Tests — ACME__Challenge__Server
# The http-01 challenge file server: serves exactly the registered path with the
# key-authorization string, 404s everything else. Real sockets, no mocks — binds
# a free high port (the production :80 needs root and would clash in CI).
# ═══════════════════════════════════════════════════════════════════════════════

import socket
import urllib.error
import urllib.request

from sg_compute.platforms.tls.ACME__Challenge__Server import ACME__Challenge__Server


def _free_port() -> int:
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestACMEChallengeServer:

    def test_serves_registered_challenge(self):
        port   = _free_port()
        server = ACME__Challenge__Server(port=port)
        server.set_challenge('/.well-known/acme-challenge/tok123', 'key-auth-value')
        server.start()
        try:
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/.well-known/acme-challenge/tok123', timeout=3) as resp:
                assert resp.status == 200
                assert resp.read().decode() == 'key-auth-value'
        finally:
            server.stop()

    def test_404s_unregistered_paths(self):
        port   = _free_port()
        server = ACME__Challenge__Server(port=port)
        server.start()
        try:
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{port}/nope', timeout=3)
                assert False, 'expected a 404'
            except urllib.error.HTTPError as exc:
                assert exc.code == 404
        finally:
            server.stop()

    def test_context_manager_starts_and_stops(self):
        port = _free_port()
        with ACME__Challenge__Server(port=port) as server:
            server.set_challenge('/.well-known/acme-challenge/ctx', 'ctx-value')
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/.well-known/acme-challenge/ctx', timeout=3) as resp:
                assert resp.read().decode() == 'ctx-value'
        # outside the block the listener is gone
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/.well-known/acme-challenge/ctx', timeout=2)
            assert False, 'server should be stopped'
        except Exception:
            pass
