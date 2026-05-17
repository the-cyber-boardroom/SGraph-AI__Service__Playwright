# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Cost__Calculator
# Estimates the USD cost of a Bedrock converse call from token counts and a
# per-region / per-model pricing table.
#
# Pricing is best-effort: pulled from the public Bedrock pricing page as of
# 2026-05-17.  Update when AWS revises prices.  The estimate is logged to the
# capture file; it is not a billing invoice.
#
# Hard cap: SG_AWS__BEDROCK__MAX_CALL_COST (default $1.00).  If the predicted
# cost exceeds the cap the call is refused unless --cost-override is supplied.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

# ── Per-million-token pricing table (input_usd, output_usd) ──────────────────
# Source: https://aws.amazon.com/bedrock/pricing/ (2026-05-17)
# Keys are prefix-matched against the model ID so partial IDs work.

_PRICING: list = [
    # (model_id_prefix, input_usd_per_1M, output_usd_per_1M)
    ('anthropic.claude-opus-4-7'                       , 15.00,  75.00),
    ('us.anthropic.claude-opus-4-7'                    , 15.00,  75.00),
    ('eu.anthropic.claude-opus-4-7'                    , 15.00,  75.00),
    ('ap.anthropic.claude-opus-4-7'                    , 15.00,  75.00),
    ('anthropic.claude-3-opus'                         , 15.00,  75.00),
    ('anthropic.claude-sonnet-4-6'                     ,  3.00,  15.00),
    ('anthropic.claude-3-7-sonnet'                     ,  3.00,  15.00),
    ('anthropic.claude-3-5-sonnet'                     ,  3.00,  15.00),
    ('anthropic.claude-3-sonnet'                       ,  3.00,  15.00),
    ('anthropic.claude-haiku-4-5'                      ,  0.80,   4.00),
    ('anthropic.claude-3-5-haiku'                      ,  0.80,   4.00),
    ('anthropic.claude-3-haiku'                        ,  0.25,   1.25),
    ('amazon.nova-premier'                             ,  2.50,  12.50),
    ('amazon.nova-pro'                                 ,  0.80,   3.20),
    ('amazon.nova-lite'                                ,  0.06,   0.24),
    ('amazon.nova-micro'                               ,  0.035,  0.14),
    ('meta.llama4-maverick'                            ,  0.17,   0.60),
    ('meta.llama4-scout'                               ,  0.17,   0.60),
    ('meta.llama3-1'                                   ,  0.22,   0.22),
    ('meta.llama3-2'                                   ,  0.18,   0.18),
    ('meta.llama3'                                     ,  0.30,   0.60),
    ('openai.gpt-4o-mini'                              ,  0.15,   0.60),
    ('openai.gpt-4o'                                   ,  5.00,  15.00),
]

DEFAULT_MAX_COST_USD = 1.00                                                       # Hard cap per call — override via env var


class Bedrock__Cost__Calculator(Type_Safe):

    def estimate(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Return estimated USD cost for a call; 0.0 if model not in pricing table."""  # inline
        in_price, out_price = self.pricing_for(model_id)
        cost = (input_tokens / 1_000_000.0) * in_price + (output_tokens / 1_000_000.0) * out_price
        return round(cost, 6)

    def pricing_for(self, model_id: str) -> tuple:                               # Returns (input_usd_per_1M, output_usd_per_1M)
        mid = model_id.lower()
        for prefix, inp, out in _PRICING:
            if mid.startswith(prefix.lower()):
                return (inp, out)
        return (0.0, 0.0)                                                        # Unknown model — log $0 rather than crash

    def max_call_cost(self) -> float:                                             # Read from env, default $1.00
        try:
            return float(os.environ.get('SG_AWS__BEDROCK__MAX_CALL_COST', DEFAULT_MAX_COST_USD))
        except (ValueError, TypeError):
            return DEFAULT_MAX_COST_USD

    def check_cost_cap(self, model_id: str, prompt_chars: int, cost_override: float = None) -> None:
        """Raise ValueError if estimated cost for a typical prompt exceeds the cap."""  # inline
        # Estimate ~1 token per 4 chars; output = 4× input (conservative)
        estimated_input  = max(1, prompt_chars // 4)
        estimated_output = estimated_input * 4
        estimate         = self.estimate(model_id, estimated_input, estimated_output)
        cap              = cost_override if cost_override is not None else self.max_call_cost()
        if estimate > cap:
            raise ValueError(
                f'Predicted cost ${estimate:.4f} exceeds cap ${cap:.2f}. '
                f'Pass --cost-override {estimate * 1.5:.2f} to allow.'
            )
