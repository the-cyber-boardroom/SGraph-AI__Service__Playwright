# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: pure render helpers
# Footer, cost-meter markup (budget bar + semantic colour), and Nova picker rows.
# PURE — no textual — runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Cost__Calculator        import Bedrock__Cost__Calculator
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Session import Schema__Bedrock__Chat__Session
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Render          import (turn_footer,
                                                                                                      cost_meter_markup,
                                                                                                      budget_fraction,
                                                                                                      cost_colour,
                                                                                                      model_picker_rows)


class test_Bedrock__Chat__Render(TestCase):

    def test_turn_footer(self):
        footer = turn_footer(100, 50, 0.000018, 420)
        assert 'in 100'      in footer
        assert 'out 50'      in footer
        assert '$0.000018'   in footer
        assert '420ms'       in footer

    def test_budget_colour_thresholds(self):
        assert cost_colour(budget_fraction(0.10, 1.0)) == 'green'
        assert cost_colour(budget_fraction(0.75, 1.0)) == 'yellow'
        assert cost_colour(budget_fraction(0.95, 1.0)) == 'red'
        assert budget_fraction(1.0, 0.0)               == 0.0                      # no divide-by-zero

    def test_cost_meter_markup(self):
        s = Schema__Bedrock__Chat__Session(model_alias='lite', region='us-east-1')
        s.total_input_tokens  = 1204
        s.total_output_tokens = 1840
        s.total_cost_usd      = 0.000713
        s.turn_count          = 3
        markup = cost_meter_markup(s)
        assert 'session'    in markup
        assert '1204'       in markup
        assert '$0.000713'  in markup
        assert 'budget'     in markup
        assert '▓' in markup or '░' in markup                                      # the budget bar rendered

    def test_model_picker_rows_nova_pricing(self):
        calc    = Bedrock__Cost__Calculator()
        resolve = lambda alias: {'default': 'amazon.nova-lite-v1:0',
                                 'lite'   : 'amazon.nova-lite-v1:0',
                                 'micro'  : 'amazon.nova-micro-v1:0',
                                 'pro'    : 'amazon.nova-pro-v1:0',
                                 'premier': 'amazon.nova-premier-v1:0'}[alias]
        rows = model_picker_rows(['default', 'lite', 'micro', 'pro', 'premier'], calc.pricing_for, resolve)
        by_alias = {r[0]: r for r in rows}
        assert by_alias['micro'][1]   == 'amazon.nova-micro-v1:0'
        assert by_alias['micro'][2:4] == (0.035, 0.14)
        assert by_alias['pro'][2:4]   == (0.80, 3.20)
