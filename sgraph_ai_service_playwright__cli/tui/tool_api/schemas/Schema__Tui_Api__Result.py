# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Result
# The outcome of one dispatch. dry_run / preview / cost_usd are added by the
# execution center in B3. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Tui_Api__Result(Type_Safe):
    ok       : bool = False
    data     : dict                                                               # free-form result payload, e.g. {'result': ...}
    error    : str
    dry_run  : bool  = False                                                      # True when this is a preview, not a committed action
    preview  : dict                                                               # change-set / field-diff when dry-run / gated
    cost_usd : float = 0.0                                                        # actual cost attributed to the call
