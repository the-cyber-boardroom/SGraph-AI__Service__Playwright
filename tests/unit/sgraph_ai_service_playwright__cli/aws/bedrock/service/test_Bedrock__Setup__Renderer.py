# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Bedrock__Setup__Renderer
# ═══════════════════════════════════════════════════════════════════════════════

import json
from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Setup__Step import List__Schema__Bedrock__Setup__Step
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Setup__Step           import Schema__Bedrock__Setup__Step
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Setup__Renderer               import Bedrock__Setup__Renderer


class test_Bedrock__Setup__Renderer(TestCase):

    def setUp(self):
        self.renderer = Bedrock__Setup__Renderer()

    # ── iam_policy_json ───────────────────────────────────────────────────────

    def test__iam_policy_json__is_valid_json(self):
        raw = self.renderer.iam_policy_json()
        parsed = json.loads(raw)                                                   # must not raise
        assert parsed is not None

    def test__iam_policy_json__contains_list_foundation_models(self):
        raw = self.renderer.iam_policy_json()
        assert 'bedrock:ListFoundationModels' in raw

    def test__iam_policy_json__contains_invoke_model(self):
        raw = self.renderer.iam_policy_json()
        assert 'bedrock:InvokeModel' in raw

    def test__iam_policy_json__effect_is_allow(self):
        parsed = json.loads(self.renderer.iam_policy_json())
        stmt   = parsed['Statement'][0]
        assert stmt['Effect'] == 'Allow'

    def test__iam_policy_json__resource_is_star(self):
        parsed = json.loads(self.renderer.iam_policy_json())
        stmt   = parsed['Statement'][0]
        assert stmt['Resource'] == '*'

    # ── model_access_deeplink ─────────────────────────────────────────────────

    def test__model_access_deeplink__contains_region(self):
        url = self.renderer.model_access_deeplink('eu-west-2')
        assert 'eu-west-2' in url

    def test__model_access_deeplink__contains_modelaccess(self):
        url = self.renderer.model_access_deeplink('us-east-1')
        assert 'modelaccess' in url

    def test__model_access_deeplink__is_https(self):
        url = self.renderer.model_access_deeplink('us-west-2')
        assert url.startswith('https://')

    # ── render_steps ──────────────────────────────────────────────────────────

    def test__render_steps__returns_typed_list(self):
        steps = self.renderer.render_steps(region='eu-west-2')
        assert isinstance(steps, List__Schema__Bedrock__Setup__Step)

    def test__render_steps__has_3_steps(self):
        steps = self.renderer.render_steps(region='us-east-1')
        assert len(steps) == 3

    def test__render_steps__each_step_is_schema(self):
        for step in self.renderer.render_steps(region='us-east-1'):
            assert isinstance(step, Schema__Bedrock__Setup__Step)

    def test__render_steps__step_numbers_are_sequential(self):
        steps = self.renderer.render_steps(region='us-east-1')
        for i, step in enumerate(steps, start=1):
            assert step.step_no == i

    def test__render_steps__step2_contains_deeplink(self):
        steps = self.renderer.render_steps(region='eu-west-2')
        step2 = steps[1]
        assert 'eu-west-2' in step2.deeplink
