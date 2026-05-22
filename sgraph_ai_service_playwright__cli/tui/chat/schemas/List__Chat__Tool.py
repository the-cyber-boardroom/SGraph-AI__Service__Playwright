# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: List__Chat__Tool — typed list of tool specs. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool import Schema__Chat__Tool


class List__Chat__Tool(Type_Safe__List):
    expected_type = Schema__Chat__Tool
