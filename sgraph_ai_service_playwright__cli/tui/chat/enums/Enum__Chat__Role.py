# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Enum__Chat__Role
# Role of one neutral chat message. Backends map it to their wire format.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Chat__Role(str, Enum):
    USER      = 'user'
    ASSISTANT = 'assistant'
    SYSTEM    = 'system'

    def __str__(self):
        return self.value
