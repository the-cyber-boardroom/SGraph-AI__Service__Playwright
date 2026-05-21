# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: stream adapter usage extraction
# The cost-critical fix: streaming must keep the token count the delta-only path
# threw away. Feeds hand-built Bedrock stream events (deltas + a terminal metadata
# event) and asserts text + exact (in, out, latency). Pure — runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Stream__Adapter import Bedrock__Stream__Adapter


def _events():
    return [{'messageStart': {'role': 'assistant'}},
            {'contentBlockDelta': {'delta': {'text': 'Hello '}}},
            {'contentBlockDelta': {'delta': {'text': 'world'}}},
            {'contentBlockStop': {}},
            {'messageStop': {'stopReason': 'end_turn'}},
            {'metadata': {'usage'  : {'inputTokens': 123, 'outputTokens': 45, 'totalTokens': 168},
                          'metrics': {'latencyMs': 512}}}]


class test_Bedrock__Stream__Adapter__usage(TestCase):

    def setUp(self):
        self.adapter = Bedrock__Stream__Adapter()

    def test_extract_usage_reads_metadata_event(self):
        assert self.adapter.extract_usage(_events()[-1]) == (123, 45, 512)
        assert self.adapter.extract_usage({'contentBlockDelta': {'delta': {'text': 'x'}}}) is None

    def test_collect_with_usage_returns_text_and_tokens(self):
        text, in_tok, out_tok, latency = self.adapter.collect_with_usage(_events())
        assert text    == 'Hello world'
        assert in_tok  == 123
        assert out_tok == 45
        assert latency == 512

    def test_collect_with_usage_zero_when_no_metadata(self):
        events = [{'contentBlockDelta': {'delta': {'text': 'hi'}}}]
        assert self.adapter.collect_with_usage(events) == ('hi', 0, 0, 0)
