# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Mitmproxy__Capture__Client.parse_ndjson (pure)
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.user_journey.core.clients.Mitmproxy__Capture__Client import Mitmproxy__Capture__Client


class TestParseNdjson:

    def test__empty_is_empty_list(self):
        assert Mitmproxy__Capture__Client().parse_ndjson('')   == []
        assert Mitmproxy__Capture__Client().parse_ndjson(None) == []

    def test__parses_lines_and_ignores_blanks(self):
        text    = '{"run_id": "r", "request": {"url": "https://a/1"}}\n' \
                  '\n' \
                  '{"run_id": "r", "request": {"url": "https://a/2"}}\n'
        records = Mitmproxy__Capture__Client().parse_ndjson(text)
        assert len(records)               == 2
        assert records[0]['request']['url'] == 'https://a/1'
        assert records[1]['request']['url'] == 'https://a/2'

    def test__round_trips_evaluator_flow_shape(self):                              # the shape the evaluator consumes
        text    = '{"request": {"url": "https://shop.test/pay"}, "response": {"status_code": 504, "headers": {"x-trace": "abc"}}}'
        records = Mitmproxy__Capture__Client().parse_ndjson(text)
        assert records[0]['response']['status_code'] == 504
        assert records[0]['response']['headers']['x-trace'] == 'abc'
