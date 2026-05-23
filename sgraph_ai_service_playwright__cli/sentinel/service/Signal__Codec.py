# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Signal__Codec
# Encode/decode the x-sentinel-signal envelope. The wire form is a raw compact JSON
# string (no base64 — CloudFront Functions lack Buffer/btoa). decode() validates by
# construction into Schema__Sentinel__Signal; extra captured keys (request_id,
# aws_request_id) the JS nests are ignored on the way in.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Signal import Schema__Sentinel__Signal


class Signal__Codec(Type_Safe):

    def decode(self, header_value: str) -> Schema__Sentinel__Signal:
        return Schema__Sentinel__Signal.from_json(json.loads(header_value))

    def encode(self, signal: Schema__Sentinel__Signal) -> str:
        return json.dumps(signal.json(), separators=(',', ':'))
