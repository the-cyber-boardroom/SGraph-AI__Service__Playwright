# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: List__Chat__Message — typed list of messages. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Message import Schema__Chat__Message


class List__Chat__Message(Type_Safe__List):
    expected_type = Schema__Chat__Message
