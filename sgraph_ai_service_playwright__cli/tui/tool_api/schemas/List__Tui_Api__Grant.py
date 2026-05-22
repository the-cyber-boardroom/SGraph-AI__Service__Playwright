# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: List__Tui_Api__Grant
# Typed list of SG/Role grants. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Grant import Schema__Tui_Api__Grant


class List__Tui_Api__Grant(Type_Safe__List):
    expected_type = Schema__Tui_Api__Grant
