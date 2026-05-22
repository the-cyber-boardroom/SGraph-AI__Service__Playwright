# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: List__Tui_Api__Call
# Typed list of audit calls (the execution center's ring buffer). Pure type def.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Call import Schema__Tui_Api__Call


class List__Tui_Api__Call(Type_Safe__List):
    expected_type = Schema__Tui_Api__Call
