# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: List__Tui_Api__Tier
# Typed list of capability tiers an API offers. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier import Enum__Tui_Api__Tier


class List__Tui_Api__Tier(Type_Safe__List):
    expected_type = Enum__Tui_Api__Tier
