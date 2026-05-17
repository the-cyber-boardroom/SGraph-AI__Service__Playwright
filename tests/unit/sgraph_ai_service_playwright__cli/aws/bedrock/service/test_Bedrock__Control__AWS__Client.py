# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Bedrock__Control__AWS__Client
# Uses _Fake_Bedrock__Control__AWS__Client — a real subclass that overrides
# the boto3 seam. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Model import List__Schema__Bedrock__Model
from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Provider             import Enum__Bedrock__Provider
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Model            import Schema__Bedrock__Model
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Control__AWS__Client     import Bedrock__Control__AWS__Client, FALLBACK_REGION

# ── Canned model summaries ────────────────────────────────────────────────────

_FAKE_MODELS = [
    {'modelId': 'anthropic.claude-haiku-4-5:0'     , 'modelName': 'Claude Haiku 4.5',
     'providerName': 'Anthropic', 'inputModalities': ['TEXT'], 'outputModalities': ['TEXT']},
    {'modelId': 'amazon.nova-lite-v1:0'             , 'modelName': 'Nova Lite',
     'providerName': 'Amazon',    'inputModalities': ['TEXT', 'IMAGE'], 'outputModalities': ['TEXT']},
    {'modelId': 'meta.llama3-8b-instruct-v1:0'     , 'modelName': 'Llama 3 8B',
     'providerName': 'Meta',      'inputModalities': ['TEXT'], 'outputModalities': ['TEXT']},
]


class _FakeBedrockControlClient:                                                 # In-memory stand-in for boto3 'bedrock' control-plane client
    def list_foundation_models(self, **kwargs):
        provider = kwargs.get('byProvider', '').lower()
        items    = _FAKE_MODELS
        if provider:
            items = [m for m in items if provider in m['providerName'].lower()]
        return {'modelSummaries': items}


class _Fake_Bedrock__Control__AWS__Client(Bedrock__Control__AWS__Client):        # Real subclass — overrides the boto3 seam
    def client(self, region: str = None):
        return _FakeBedrockControlClient()

    def current_region(self) -> str:
        return FALLBACK_REGION


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Bedrock__Control__AWS__Client(TestCase):

    def setUp(self):
        self.client = _Fake_Bedrock__Control__AWS__Client()

    # ── list_models ───────────────────────────────────────────────────────────

    def test__list_models__returns_typed_list(self):
        models = self.client.list_models()
        assert isinstance(models, List__Schema__Bedrock__Model)

    def test__list_models__contains_all_fake_models(self):
        models = self.client.list_models()
        assert len(models) == 3

    def test__list_models__each_item_is_schema(self):
        for m in self.client.list_models():
            assert isinstance(m, Schema__Bedrock__Model)

    def test__list_models__provider_filter_narrows_results(self):
        models = self.client.list_models(provider_filter='Anthropic')
        assert len(models) == 1
        assert 'haiku' in str(models[0].model_id)

    def test__list_models__region_populated(self):
        models = self.client.list_models()
        for m in models:
            assert m.region == FALLBACK_REGION

    def test__list_models__input_modalities_formatted(self):
        models = self.client.list_models()
        nova   = next(m for m in models if 'nova' in str(m.model_id))
        assert 'TEXT' in nova.input_modalities
        assert 'IMAGE' in nova.input_modalities

    # ── infer_provider ────────────────────────────────────────────────────────

    def test__infer_provider__anthropic_returns_claude(self):
        p = self.client.infer_provider('Anthropic', 'anthropic.claude-haiku')
        assert p == Enum__Bedrock__Provider.CLAUDE

    def test__infer_provider__amazon_nova_returns_nova(self):
        p = self.client.infer_provider('Amazon', 'amazon.nova-lite-v1:0')
        assert p == Enum__Bedrock__Provider.NOVA

    def test__infer_provider__meta_llama_returns_llama(self):
        p = self.client.infer_provider('Meta', 'meta.llama3-8b')
        assert p == Enum__Bedrock__Provider.LLAMA

    def test__infer_provider__unknown_returns_other(self):
        p = self.client.infer_provider('Unknown', 'some.model')
        assert p == Enum__Bedrock__Provider.OTHER
