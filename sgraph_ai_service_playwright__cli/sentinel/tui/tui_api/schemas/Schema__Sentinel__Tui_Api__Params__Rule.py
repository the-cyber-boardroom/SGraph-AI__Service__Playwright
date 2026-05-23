# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Tui_Api__Params__Rule
# Params for rule-targeting actions (rule_show). Tui_Api__Schema__Builder emits its
# JSON Schema for the model. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Sentinel__Tui_Api__Params__Rule(Type_Safe):
    rule_id : str                                                                    # e.g. '0012'
