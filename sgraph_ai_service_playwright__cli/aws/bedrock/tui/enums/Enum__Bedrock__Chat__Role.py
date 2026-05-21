# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Enum__Bedrock__Chat__Role
# Role of one line in a chat conversation. Maps to the Bedrock message `role`.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Bedrock__Chat__Role(str, Enum):
    USER      = 'user'
    ASSISTANT = 'assistant'
    SYSTEM    = 'system'

    def __str__(self):
        return self.value
