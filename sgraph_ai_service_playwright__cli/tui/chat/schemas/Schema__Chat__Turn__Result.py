# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Turn__Result — one converse() outcome (neutral).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.chat.schemas.List__Chat__Content import List__Chat__Content
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Usage import Schema__Chat__Usage


class Schema__Chat__Turn__Result(Type_Safe):
    stop_reason : str = 'end_turn'                                                # 'end_turn' | 'tool_use'
    content     : List__Chat__Content
    usage       : Schema__Chat__Usage
