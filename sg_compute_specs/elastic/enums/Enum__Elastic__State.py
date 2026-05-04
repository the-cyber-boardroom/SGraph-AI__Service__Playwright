# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Enum__Elastic__State
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Elastic__State(str, Enum):
    PENDING     = 'pending'
    RUNNING     = 'running'
    READY       = 'ready'
    TERMINATING = 'terminating'
    TERMINATED  = 'terminated'
    UNKNOWN     = 'unknown'

    def __str__(self):
        return self.value
