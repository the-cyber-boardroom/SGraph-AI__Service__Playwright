# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the chat verb flow (run_chat helper)
# Uses in-memory subclasses of all service classes; no mocks, no patches.
# Verifies: model resolution, capture write, cost calculation, schema shape.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import tempfile
from pathlib                                                                     import Path
from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.cli.chat.verbs.Verb__Bedrock__Chat__Helpers import run_chat
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Chat__Response      import Schema__Bedrock__Chat__Response
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Capture__Writer             import Bedrock__Capture__Writer
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Cost__Calculator            import Bedrock__Cost__Calculator
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Model__Resolver             import Bedrock__Model__Resolver
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Runtime__AWS__Client        import Bedrock__Runtime__AWS__Client, FALLBACK_REGION

# ── In-memory stub ────────────────────────────────────────────────────────────

_FAKE_ALIASES = {
    'claude': {
        'default'   : 'anthropic.claude-3-5-haiku-20241022-v1:0',
        'haiku-4.5' : 'anthropic.claude-haiku-4-5:0'            ,
    },
    'nova': {'default': 'amazon.nova-lite-v1:0'},
    'region_overrides': {},
}

_FAKE_RESPONSE = {
    'output': {'message': {'role': 'assistant', 'content': [{'text': 'Four.'}]}},
    'usage' : {'inputTokens': 5, 'outputTokens': 3},
}


class _FakeBotoRuntime:
    def converse(self, modelId, messages):
        return _FAKE_RESPONSE

    def converse_stream(self, modelId, messages):
        return {'stream': iter([{'contentBlockDelta': {'delta': {'text': 'Four.'}}}])}


class _Fake__Runtime(Bedrock__Runtime__AWS__Client):
    def client(self, region=None):
        return _FakeBotoRuntime()

    def current_region(self) -> str:
        return FALLBACK_REGION


class _Fake__Resolver(Bedrock__Model__Resolver):
    def aliases(self) -> dict:
        return _FAKE_ALIASES


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Bedrock__Chat__Flow(TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime  = _Fake__Runtime()
        self.resolver = _Fake__Resolver()
        self.writer   = Bedrock__Capture__Writer(root=self._tmpdir)
        self.calc     = Bedrock__Cost__Calculator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _run(self, provider='claude', alias='default', prompt='What is 2+2?',
             stream=False, json_output=False, cost_override=None) -> Schema__Bedrock__Chat__Response:
        return run_chat(provider, alias, prompt, stream, json_output, cost_override,
                        runtime=self.runtime, resolver=self.resolver,
                        writer=self.writer, calc=self.calc)

    # ── Schema shape ─────────────────────────────────────────────────────────

    def test__run_chat__returns_schema(self):
        schema = self._run()
        assert isinstance(schema, Schema__Bedrock__Chat__Response)

    def test__run_chat__response_text_non_empty(self):
        schema = self._run()
        assert schema.response_text == 'Four.'

    def test__run_chat__input_tokens_correct(self):
        schema = self._run()
        assert schema.input_tokens == 5

    def test__run_chat__output_tokens_correct(self):
        schema = self._run()
        assert schema.output_tokens == 3

    def test__run_chat__region_populated(self):
        schema = self._run()
        assert schema.region == FALLBACK_REGION

    def test__run_chat__model_id_populated(self):
        schema = self._run()
        assert str(schema.model_id) != ''

    def test__run_chat__cost_usd_is_float(self):
        schema = self._run()
        assert isinstance(schema.cost_usd, float)

    def test__run_chat__run_id_non_empty(self):
        schema = self._run()
        assert schema.run_id != ''

    def test__run_chat__capture_path_is_file(self):
        schema = self._run()
        assert Path(schema.capture_path).exists()

    # ── Capture file content ──────────────────────────────────────────────────

    def test__run_chat__capture_file_contains_prompt(self):
        schema  = self._run(prompt='hello world')
        payload = json.loads(Path(schema.capture_path).read_text())
        assert payload['prompt'] == 'hello world'

    def test__run_chat__capture_file_contains_response(self):
        schema  = self._run()
        payload = json.loads(Path(schema.capture_path).read_text())
        assert payload['response_text'] == 'Four.'

    # ── Alias resolution ──────────────────────────────────────────────────────

    def test__run_chat__haiku_45_alias_resolves(self):
        schema = self._run(provider='claude', alias='haiku-4.5')
        assert 'haiku' in str(schema.model_id).lower()

    def test__run_chat__nova_default_resolves(self):
        schema = self._run(provider='nova')
        assert 'nova' in str(schema.model_id).lower()

    # ── Mutation gate not involved for chat ───────────────────────────────────

    def test__run_chat__does_not_need_mutation_gate(self):
        os.environ.pop('SG_AWS__BEDROCK__ALLOW_MUTATIONS', None)
        schema = self._run()                                                     # must not raise
        assert schema.response_text == 'Four.'
