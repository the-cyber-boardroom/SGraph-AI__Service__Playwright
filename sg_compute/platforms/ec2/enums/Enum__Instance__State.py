# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Enum__Instance__State
# EC2 instance lifecycle state as reported by the AWS API, plus UNKNOWN as a
# fallback for states not explicitly modelled.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Instance__State(str, Enum):
    PENDING       = 'pending'
    RUNNING       = 'running'
    SHUTTING_DOWN = 'shutting-down'
    TERMINATED    = 'terminated'
    STOPPING      = 'stopping'
    STOPPED       = 'stopped'
    UNKNOWN       = 'unknown'

    def __str__(self):
        return self.value
