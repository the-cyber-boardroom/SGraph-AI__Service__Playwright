# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — B↔C parity (local-direct vs local-docker)
# The canonical request set, driven through both targets with a FIXED request_id +
# received_at, must produce identical signals. docker- and node-gated via a pytest
# skipif marker (so the class-scoped container lifecycle is skipped too) — runs
# only where docker's daemon is reachable.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source     import node_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Docker__Runtime import Sentinel__Docker__Runtime, docker_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness  import Sentinel__Local__Harness, build_captured
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink    import InMemory__Log__Sink

_CANONICAL = [('GET', '/index.html',   '198.51.100.2'),
              ('GET', '/etc/passwd',   '185.10.10.10'),
              ('GET', '/wp-login.php', '91.20.20.20' ),
              ('GET', '/.env',         '77.30.30.30' ),
              ('GET', '/index.html',   '10.0.0.6'    ),
              ('GET', '',              '203.0.113.5' )]


def _fixed_captured(method, path, ip):                                              # deterministic id + timestamp for comparison
    return build_captured(method, path, ip, request_id='sn-parity', received_at='2026-01-01T00:00:00Z')


@pytest.mark.skipif(not (node_available() and docker_available()), reason='node + docker required for B↔C parity')
class TestParityDockerEqualsDirect:
    @classmethod
    def setup_class(cls):
        cls.runtime = Sentinel__Docker__Runtime()
        cls.runtime.up()

    @classmethod
    def teardown_class(cls):
        cls.runtime.down()

    def test_docker_signals_equal_direct_signals(self):
        from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Docker__Harness import Sentinel__Docker__Harness
        direct = Sentinel__Local__Harness (log_sink=InMemory__Log__Sink())
        docker = Sentinel__Docker__Harness(log_sink=InMemory__Log__Sink(), runtime=self.runtime)
        for method, path, ip in _CANONICAL:
            captured = _fixed_captured(method, path, ip)
            assert docker.evaluate_signal(captured).json() == direct.evaluate_signal(captured).json(), f'{path} ({ip})'
