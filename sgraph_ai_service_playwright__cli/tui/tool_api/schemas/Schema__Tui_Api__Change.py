# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Change
# A structured change-control entry captured at the moment of change. Capture is
# RECOMMENDED, not enforced (decision #5). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Change_Kind import Enum__Tui_Api__Change_Kind


class Schema__Tui_Api__Change(Type_Safe):
    kind    : Enum__Tui_Api__Change_Kind = Enum__Tui_Api__Change_Kind.FEATURE
    summary : str
    version : str
    ts      : float = 0.0
