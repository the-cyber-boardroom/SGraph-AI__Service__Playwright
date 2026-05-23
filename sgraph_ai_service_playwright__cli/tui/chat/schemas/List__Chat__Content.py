# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: List__Chat__Content — typed list of content blocks. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Content import Schema__Chat__Content


class List__Chat__Content(Type_Safe__List):
    expected_type = Schema__Chat__Content
