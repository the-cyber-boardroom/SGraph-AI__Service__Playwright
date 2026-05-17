# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Bedrock__Runtime__AWS__Client
# Uses _Fake_Bedrock__Runtime__AWS__Client — a real subclass that overrides
# the boto3 seam with an in-memory stub. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Runtime__AWS__Client import Bedrock__Runtime__AWS__Client, FALLBACK_REGION

# ── Canned boto3 converse responses ──────────────────────────────────────────

_FAKE_CONVERSE_RESPONSE = {
    'output': {
        'message': {
            'role'   : 'assistant',
            'content': [{'text': 'Hello, world!'}],
        }
    },
    'usage': {'inputTokens': 10, 'outputTokens': 20},
    'stopReason': 'end_turn',
}

_FAKE_STREAM_EVENTS = [
    {'contentBlockDelta': {'delta': {'text': 'Hello'}, 'contentBlockIndex': 0}},
    {'contentBlockDelta': {'delta': {'text': ', world!'}, 'contentBlockIndex': 0}},
    {'messageStop': {'stopReason': 'end_turn'}},
]


class _FakeBotoRuntimeClient:                                                    # In-memory stand-in for bedrock-runtime boto3 client
    def converse(self, modelId, messages):
        return _FAKE_CONVERSE_RESPONSE

    def converse_stream(self, modelId, messages):
        return {'stream': iter(_FAKE_STREAM_EVENTS)}


class _Fake_Bedrock__Runtime__AWS__Client(Bedrock__Runtime__AWS__Client):        # Real subclass — overrides boto3 seam; no mocks
    def client(self, region: str = None):
        return _FakeBotoRuntimeClient()

    def current_region(self) -> str:
        return FALLBACK_REGION


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Bedrock__Runtime__AWS__Client(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Runtime__AWS__Client()

    # ── converse ─────────────────────────────────────────────────────────────

    def test__converse__returns_dict(self):
        resp = self.client.converse('anthropic.claude-haiku-4-5:0', 'hello')
        assert isinstance(resp, dict)

    def test__converse__output_present(self):
        resp = self.client.converse('anthropic.claude-haiku-4-5:0', 'hello')
        assert 'output' in resp

    def test__converse__usage_present(self):
        resp = self.client.converse('anthropic.claude-haiku-4-5:0', 'hello')
        assert 'usage' in resp

    # ── extract_text ─────────────────────────────────────────────────────────

    def test__extract_text__returns_assistant_text(self):
        resp = self.client.converse('anthropic.claude-haiku-4-5:0', 'hello')
        text = self.client.extract_text(resp)
        assert text == 'Hello, world!'

    def test__extract_text__empty_response_returns_empty_string(self):
        text = self.client.extract_text({})
        assert text == ''

    # ── extract_usage ─────────────────────────────────────────────────────────

    def test__extract_usage__returns_tuple(self):
        resp  = self.client.converse('anthropic.claude-haiku-4-5:0', 'hello')
        usage = self.client.extract_usage(resp)
        assert isinstance(usage, tuple)
        assert len(usage) == 2

    def test__extract_usage__input_tokens_correct(self):
        resp               = self.client.converse('anthropic.claude-haiku-4-5:0', 'hello')
        input_tok, out_tok = self.client.extract_usage(resp)
        assert input_tok == 10
        assert out_tok   == 20

    def test__extract_usage__missing_usage_returns_zeros(self):
        input_tok, out_tok = self.client.extract_usage({})
        assert input_tok == 0
        assert out_tok   == 0

    # ── converse_stream ───────────────────────────────────────────────────────

    def test__converse_stream__yields_events(self):
        events = list(self.client.converse_stream('anthropic.claude-haiku-4-5:0', 'hello'))
        assert len(events) > 0

    def test__converse_stream__events_contain_text_deltas(self):
        events = list(self.client.converse_stream('anthropic.claude-haiku-4-5:0', 'hello'))
        deltas = [e for e in events if 'contentBlockDelta' in e]
        assert len(deltas) >= 1
