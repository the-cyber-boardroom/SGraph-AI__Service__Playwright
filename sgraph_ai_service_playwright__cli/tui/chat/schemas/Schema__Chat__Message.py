# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Message — role + neutral content blocks. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.chat.enums.Enum__Chat__Role        import Enum__Chat__Role
from sgraph_ai_service_playwright__cli.tui.chat.schemas.List__Chat__Content   import List__Chat__Content


class Schema__Chat__Message(Type_Safe):
    role    : Enum__Chat__Role = Enum__Chat__Role.USER
    content : List__Chat__Content
