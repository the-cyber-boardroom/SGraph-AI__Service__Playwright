# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Grant
# A scope granted to an identity, time-bounded (decision #2). expires_at 0 = session
# lifetime; derived_from carries a parent token id for sub-agent delegation. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope import Schema__Tui_Api__Scope


class Schema__Tui_Api__Grant(Type_Safe):
    scope        : Schema__Tui_Api__Scope
    expires_at   : float = 0.0                                                    # 0 = session lifetime; else epoch seconds
    derived_from : str                                                            # parent token id, for delegation
