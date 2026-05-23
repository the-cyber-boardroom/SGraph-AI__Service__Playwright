# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Sentinel__Signal (and the captured sub-schema)
# The signal is the parity spine. These assert it constructs from snake_case data,
# validates by construction, and round-trips through json() losslessly.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action       import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Layer        import Enum__Sentinel__Layer
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict      import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Captured import Schema__Sentinel__Captured
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Signal   import Schema__Sentinel__Signal


def _captured(**kw) -> Schema__Sentinel__Captured:
    return Schema__Sentinel__Captured(method      = kw.get('method',      'GET'),
                                      path        = kw.get('path',        '/etc/passwd'),
                                      host        = kw.get('host',        'static.example.com'),
                                      source_ip   = kw.get('source_ip',   '185.10.10.10'),
                                      user_agent  = kw.get('user_agent',  'curl/8.0'),
                                      querystring = kw.get('querystring', ''),
                                      received_at = kw.get('received_at', '2026-05-23T10:00:00Z'),
                                      cache_status= kw.get('cache_status','miss'))


class TestDefaults:
    def test_empty_signal_constructs_with_safe_defaults(self):
        sig = Schema__Sentinel__Signal()
        assert sig.verdict == Enum__Sentinel__Verdict.ALLOW
        assert sig.action  == Enum__Sentinel__Action.PASS
        assert sig.layer   == Enum__Sentinel__Layer.L1
        assert str(sig.request_id) == ''


class TestConstructFromCaptured:
    def test_block_signal_fields(self):
        sig = Schema__Sentinel__Signal(request_id      = 'sn-deadbeef',
                                       captured        = _captured(),
                                       verdict         = Enum__Sentinel__Verdict.BLOCK,
                                       reason          = 'path never valid',
                                       rule_id         = '0012',
                                       action          = Enum__Sentinel__Action.DROP_403,
                                       engine_version  = '0.1.0',
                                       ruleset_version = '0.1.0')
        assert sig.verdict             == Enum__Sentinel__Verdict.BLOCK
        assert str(sig.rule_id)        == '0012'
        assert str(sig.reason)         == 'path never valid'                       # spaces preserved
        assert str(sig.captured.path)  == '/etc/passwd'                            # path preserved verbatim


class TestRoundTrip:
    def test_json_round_trip_is_lossless(self):
        sig   = Schema__Sentinel__Signal(request_id = 'sn-abc123',
                                         captured   = _captured(),
                                         verdict    = Enum__Sentinel__Verdict.BLOCK,
                                         reason     = 'path never valid',
                                         rule_id    = '0012',
                                         action     = Enum__Sentinel__Action.DROP_403)
        data  = sig.json()
        again = Schema__Sentinel__Signal.from_json(data)
        assert again.json() == data

    def test_json_keys_are_snake_case(self):
        data = Schema__Sentinel__Signal().json()
        for key in ('request_id', 'aws_request_id', 'captured', 'verdict', 'reason',
                    'rule_id', 'action', 'layer', 'engine_version', 'ruleset_version'):
            assert key in data
