# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Result
# The outcome of one dispatch. dry_run / preview / cost_usd are added by the
# execution center in B3. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Tui_Api__Result(Type_Safe):
    ok    : bool = False
    data  : dict                                                                  # free-form result payload, e.g. {'result': ...}
    error : str
