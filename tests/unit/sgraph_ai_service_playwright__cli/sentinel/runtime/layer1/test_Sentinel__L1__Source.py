# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__L1__Source (the L1 JS engine)
# Drives the real engine via `node` over the canonical request set and asserts the
# emitted signal deserialises into Schema__Sentinel__Signal with the expected
# verdict / rule_id / action. node-gated (CI image ships node).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import skipUnless

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source import Sentinel__L1__Source, node_available
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Signal    import Schema__Sentinel__Signal

# (method, path, source_ip, expected_verdict, expected_rule, expected_action)
_CASES = [('GET', '/index.html',   '198.51.100.2', 'allow', '0001', 'pass'       ),
          ('GET', '/etc/passwd',   '185.10.10.10', 'block', '0012', 'drop_403'   ),
          ('GET', '/wp-login.php', '91.20.20.20',  'block', '0018', 'deflect_404'),
          ('GET', '/.env',         '77.30.30.30',  'block', '0014', 'deflect_404'),
          ('GET', '/index.html',   '10.0.0.6',     'block', '0003', 'drop_403'   ),
          ('GET', '',              '203.0.113.5',  'block', '0007', 'drop_403'   )]


def _captured(method: str, path: str, ip: str) -> dict:
    return {'request_id': 'sn-test', 'aws_request_id': '', 'method': method, 'path': path,
            'querystring': '', 'host': 'static.example.com', 'source_ip': ip,
            'user_agent': 'pytest', 'received_at': '2026-01-01T00:00:00Z', 'cache_status': 'miss'}


class TestMaterialisation:
    def test_raw_source_has_empty_banned_marker(self):
        assert 'var BANNED_IPS = [];' in Sentinel__L1__Source().raw_source()

    def test_materialised_source_inlines_banned_ips(self):
        src = Sentinel__L1__Source().materialised_source()
        assert 'var BANNED_IPS = [];' not in src
        assert '10.0.0.6' in src

    def test_banned_ips_loaded_from_json(self):
        assert '10.0.0.6' in Sentinel__L1__Source().banned_ips()


@skipUnless(node_available(), 'node not available')
class TestEvaluate:
    def test_each_canonical_case_matches_expected_verdict(self):
        source = Sentinel__L1__Source()
        for method, path, ip, verdict, rule, action in _CASES:
            sig = source.evaluate(_captured(method, path, ip))
            assert sig['verdict'] == verdict, f'{path} ({ip})'
            assert sig['rule_id'] == rule,    f'{path} ({ip})'
            assert sig['action']  == action,  f'{path} ({ip})'

    def test_signal_deserialises_into_schema(self):
        sig    = Sentinel__L1__Source().evaluate(_captured('GET', '/etc/passwd', '185.10.10.10'))
        schema = Schema__Sentinel__Signal.from_json(sig)
        assert str(schema.rule_id)       == '0012'
        assert str(schema.captured.path) == '/etc/passwd'
        assert str(schema.reason)        == 'path never valid'

    def test_engine_never_signals_a_response_only_a_verdict(self):
        sig = Sentinel__L1__Source().evaluate(_captured('GET', '/index.html', '198.51.100.2'))
        assert set(sig.keys()) >= {'request_id', 'captured', 'verdict', 'rule_id', 'action', 'layer'}
        assert sig['layer'] == 'L1'
