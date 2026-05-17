# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Bedrock__Memory__Scope
# AgentCore memory scope — short-term, long-term, or both.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Bedrock__Memory__Scope(str, Enum):
    SHORT = 'short'
    LONG  = 'long'
    BOTH  = 'both'

    def __str__(self):
        return self.value
