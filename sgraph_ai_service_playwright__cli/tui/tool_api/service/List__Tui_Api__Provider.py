# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: List__Tui_Api__Provider
# Typed list of registered providers (subclasses pass the isinstance check).
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider import Tui_Api__Provider


class List__Tui_Api__Provider(Type_Safe__List):
    expected_type = Tui_Api__Provider
