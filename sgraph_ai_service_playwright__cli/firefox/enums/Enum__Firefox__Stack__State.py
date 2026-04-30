# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Firefox__Stack__State
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Firefox__Stack__State(Enum):
    PENDING     = 'pending'
    RUNNING     = 'running'
    READY       = 'ready'
    TERMINATING = 'terminating'
    TERMINATED  = 'terminated'
    UNKNOWN     = 'unknown'

    def __str__(self):
        return self.value
