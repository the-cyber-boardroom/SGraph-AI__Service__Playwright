# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Call
# One audit ring-buffer entry (the getLog() analogue). params are sanitised before
# storage. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Exec_Mode import Enum__Tui_Api__Exec_Mode
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope import Schema__Tui_Api__Scope


class Schema__Tui_Api__Call(Type_Safe):
    action_ref  : str
    params      : dict                                                            # sanitised — secrets masked
    scope_used  : Schema__Tui_Api__Scope
    mode        : Enum__Tui_Api__Exec_Mode = Enum__Tui_Api__Exec_Mode.AUTO
    result_ok   : bool = False
    error       : str
    duration_ms : int   = 0
    cost_usd    : float = 0.0
    identity    : str   = 'local'
    ts          : float = 0.0
