# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Bedrock__Provider
# Supported Bedrock model provider families.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Bedrock__Provider(str, Enum):
    CLAUDE  = 'CLAUDE'
    NOVA    = 'NOVA'
    LLAMA   = 'LLAMA'
    OPENAI  = 'OPENAI'
    OTHER   = 'OTHER'

    def __str__(self):
        return self.value
