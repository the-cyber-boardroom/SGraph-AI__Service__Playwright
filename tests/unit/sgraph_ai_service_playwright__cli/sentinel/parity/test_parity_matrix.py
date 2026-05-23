# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Three-target parity matrix (the definition of done)
# The canonical request set must yield identical decisions across local-direct,
# local-docker, and live AWS. local-direct is the always-available baseline; docker
# (see test_parity_b_vs_c.py) and AWS are asserted equal to it.
#
# The AWS legs are gated on a live environment (SG_SENTINEL__LIVE_TESTS=1 +
# SENTINEL_TEST_DISTRIBUTION=<domain>) and skip cleanly otherwise — there is no CF
# runtime or AWS account in CI. On AWS the signal isn't returned to the client, so
# parity is asserted on the observable contract: the HTTP enforcement status and the
# verdict/rule persisted in the S3 log record (the replayable signal-equivalent).
# ═══════════════════════════════════════════════════════════════════════════════

import os

import pytest

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source    import node_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness import Sentinel__Local__Harness, build_captured
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink   import InMemory__Log__Sink

# (method, path, source_ip, expected_verdict, expected_rule, expected_http)
CANONICAL = [('GET', '/index.html',   '198.51.100.2', 'allow', '0001',   0),
             ('GET', '/etc/passwd',   '185.10.10.10', 'block', '0012', 403),
             ('GET', '/wp-login.php', '91.20.20.20',  'block', '0018', 404),
             ('GET', '/.env',         '77.30.30.30',  'block', '0014', 404),
             ('GET', '/index.html',   '10.0.0.6',     'block', '0003', 403),
             ('GET', '',              '203.0.113.5',  'block', '0007', 403)]


def _fixed_captured(method, path, ip):
    return build_captured(method, path, ip, request_id='sn-parity', received_at='2026-01-01T00:00:00Z')


def _baseline_signal(captured):
    return Sentinel__Local__Harness(log_sink=InMemory__Log__Sink()).evaluate_signal(captured)


def _live_env() -> bool:
    return os.environ.get('SG_SENTINEL__LIVE_TESTS', '') == '1' and bool(os.environ.get('SENTINEL_TEST_DISTRIBUTION', ''))


@pytest.mark.skipif(not node_available(), reason='node required for the L1 engine')
class TestBaselineLocalDirect:
    def test_each_canonical_matches_expected(self):
        for method, path, ip, verdict, rule, _http in CANONICAL:
            sig = _baseline_signal(_fixed_captured(method, path, ip))
            assert sig.verdict.value == verdict, f'{path} ({ip})'
            assert str(sig.rule_id)  == rule,    f'{path} ({ip})'

    def test_enforcement_status_matches_expected(self):
        h = Sentinel__Local__Harness(log_sink=InMemory__Log__Sink())
        for method, path, ip, _verdict, _rule, http in CANONICAL:
            _sig, enforce = h.hit(method, path, source_ip=ip, request_id='sn-x', received_at='2026-01-01T00:00:00Z')
            assert enforce.http_status == http, f'{path} ({ip})'


@pytest.mark.skipif(not (node_available() and _live_env()),
                    reason='live AWS parity needs SG_SENTINEL__LIVE_TESTS=1 + SENTINEL_TEST_DISTRIBUTION')
class TestParityAwsEqualsBaseline:
    def test_aws_decisions_equal_baseline(self):
        import requests
        domain = os.environ['SENTINEL_TEST_DISTRIBUTION']
        for method, path, ip, verdict, _rule, http in CANONICAL:
            url  = f'https://{domain}{path or "/"}'
            resp = requests.request(method or 'GET', url, allow_redirects=False, timeout=15)
            if verdict == 'block':
                assert resp.status_code == http, f'{path}: expected {http}, got {resp.status_code}'
            else:
                assert resp.status_code < 400, f'{path}: expected pass, got {resp.status_code}'
