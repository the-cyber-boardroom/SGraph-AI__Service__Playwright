# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Dns__Check__Mode
# Which resolver set is used for a DNS check operation.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Dns__Check__Mode(Enum):
    AUTHORITATIVE    = 'authoritative'
    PUBLIC_RESOLVERS = 'public_resolvers'
    LOCAL            = 'local'

    def __str__(self):
        return self.value
