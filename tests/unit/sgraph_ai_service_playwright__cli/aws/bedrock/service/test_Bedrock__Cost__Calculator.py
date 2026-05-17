# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Bedrock__Cost__Calculator
# Pure-logic tests — no I/O, no boto3, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Cost__Calculator import Bedrock__Cost__Calculator


class test_Bedrock__Cost__Calculator(TestCase):

    def setUp(self):
        self.calc = Bedrock__Cost__Calculator()

    # ── pricing_for ───────────────────────────────────────────────────────────

    def test__pricing_for__haiku_35_returns_nonzero(self):
        inp, out = self.calc.pricing_for('anthropic.claude-3-5-haiku-20241022-v1:0')
        assert inp > 0
        assert out > 0

    def test__pricing_for__nova_lite_returns_nonzero(self):
        inp, out = self.calc.pricing_for('amazon.nova-lite-v1:0')
        assert inp > 0
        assert out > 0

    def test__pricing_for__unknown_returns_zeros(self):
        inp, out = self.calc.pricing_for('unknown.model-id')
        assert inp == 0.0
        assert out == 0.0

    def test__pricing_for__prefix_match_works(self):
        inp, out = self.calc.pricing_for('anthropic.claude-sonnet-4-6:0')
        assert inp > 0
        assert out > 0

    # ── estimate ─────────────────────────────────────────────────────────────

    def test__estimate__haiku_small_prompt_is_low(self):
        cost = self.calc.estimate('anthropic.claude-haiku-4-5:0', 100, 200)
        assert cost < 0.01                                                       # Very cheap for small token counts

    def test__estimate__zero_tokens_is_zero(self):
        cost = self.calc.estimate('anthropic.claude-haiku-4-5:0', 0, 0)
        assert cost == 0.0

    def test__estimate__opus_is_more_expensive_than_haiku(self):
        haiku_cost = self.calc.estimate('anthropic.claude-3-5-haiku-20241022-v1:0', 10000, 5000)
        opus_cost  = self.calc.estimate('anthropic.claude-opus-4-7', 10000, 5000)
        assert opus_cost > haiku_cost

    def test__estimate__returns_float(self):
        cost = self.calc.estimate('amazon.nova-lite-v1:0', 500, 500)
        assert isinstance(cost, float)

    # ── max_call_cost ─────────────────────────────────────────────────────────

    def test__max_call_cost__default_is_one_dollar(self):
        os.environ.pop('SG_AWS__BEDROCK__MAX_CALL_COST', None)
        assert self.calc.max_call_cost() == 1.00

    def test__max_call_cost__reads_from_env(self):
        os.environ['SG_AWS__BEDROCK__MAX_CALL_COST'] = '5.00'
        try:
            assert self.calc.max_call_cost() == 5.00
        finally:
            os.environ.pop('SG_AWS__BEDROCK__MAX_CALL_COST', None)

    def test__max_call_cost__bad_env_falls_back_to_default(self):
        os.environ['SG_AWS__BEDROCK__MAX_CALL_COST'] = 'not-a-number'
        try:
            assert self.calc.max_call_cost() == 1.00
        finally:
            os.environ.pop('SG_AWS__BEDROCK__MAX_CALL_COST', None)

    # ── check_cost_cap ────────────────────────────────────────────────────────

    def test__check_cost_cap__small_prompt_no_raise(self):
        # 10-char prompt → ~2 tokens → estimated cost is trivial
        self.calc.check_cost_cap('amazon.nova-micro-v1:0', 10)                  # must not raise

    def test__check_cost_cap__override_higher_allows_call(self):
        self.calc.check_cost_cap('anthropic.claude-opus-4-7', 4000, cost_override=100.00)

    def test__check_cost_cap__zero_cost_unknown_model_no_raise(self):
        self.calc.check_cost_cap('unknown.model', 999999)                       # pricing = $0 → always under cap
