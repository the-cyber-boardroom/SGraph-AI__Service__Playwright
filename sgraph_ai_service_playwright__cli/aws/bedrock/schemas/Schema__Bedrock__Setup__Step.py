# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Bedrock__Setup__Step
# One numbered step in the `sg aws bedrock setup` guided flow.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe


class Schema__Bedrock__Setup__Step(Type_Safe):
    step_no  : int                                                                 # 1-based step number
    title    : str                                                                 # Short title e.g. 'IAM permissions'
    body     : str                                                                 # Multi-line explanatory text
    deeplink : str                                                                 # AWS console deeplink (may be empty)
