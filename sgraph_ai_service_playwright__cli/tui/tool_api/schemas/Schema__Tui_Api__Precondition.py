# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Precondition
# A flat state gate (decision #3 — no DAG). An action is available only when all of
# its preconditions hold against provider.state(). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Cond_Op import Enum__Tui_Api__Cond_Op


class Schema__Tui_Api__Precondition(Type_Safe):
    state_path : str                                                              # dotted path into provider.state(), e.g. 'slug.state'
    op         : Enum__Tui_Api__Cond_Op = Enum__Tui_Api__Cond_Op.EQ
    value      : str                                                              # compared value (comma-separated set for IN / NOT_IN)
    note       : str                                                              # human reason, surfaced on refusal
