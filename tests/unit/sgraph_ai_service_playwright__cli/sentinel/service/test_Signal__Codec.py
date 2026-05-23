# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Signal__Codec
# Decodes a raw-JSON x-sentinel-signal (as the JS emits, with extra captured keys)
# and round-trips through encode/decode.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict   import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.service.Signal__Codec           import Signal__Codec

_WIRE = {
    'request_id': 'sn-x', 'aws_request_id': '', 'verdict': 'block', 'reason': 'path never valid',
    'rule_id': '0012', 'action': 'drop_403', 'layer': 'L1',
    'engine_version': '0.1.0', 'ruleset_version': '0.1.0',
    'captured': {'request_id': 'sn-x', 'aws_request_id': '',                       # extra keys the JS nests
                 'method': 'GET', 'path': '/etc/passwd', 'host': 'h', 'source_ip': '1.2.3.4',
                 'user_agent': 'ua', 'querystring': '', 'received_at': '2026-05-23T10:00:00Z',
                 'cache_status': 'miss'},
}


class TestDecode:
    def test_decode_ignores_extra_captured_keys(self):
        sig = Signal__Codec().decode(json.dumps(_WIRE))
        assert sig.verdict             == Enum__Sentinel__Verdict.BLOCK
        assert str(sig.rule_id)        == '0012'
        assert str(sig.captured.path)  == '/etc/passwd'


class TestRoundTrip:
    def test_encode_decode_round_trip(self):
        codec = Signal__Codec()
        sig   = codec.decode(json.dumps(_WIRE))
        again = codec.decode(codec.encode(sig))
        assert again.json() == sig.json()

    def test_encode_is_compact(self):
        sig     = Signal__Codec().decode(json.dumps(_WIRE))
        encoded = Signal__Codec().encode(sig)
        assert ', ' not in encoded                                                   # compact separators (header-friendly)
