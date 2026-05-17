# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Bedrock__Tool__Type
# AgentCore inline tool types supported by this surface.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Bedrock__Tool__Type(str, Enum):
    BROWSER          = 'browser'
    CODE_INTERPRETER = 'code-interpreter'

    def __str__(self):
        return self.value
