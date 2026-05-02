# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Enum__Vnc__Stack__State
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vnc__Stack__State(str, Enum):
    PENDING      = 'pending'
    RUNNING      = 'running'
    READY        = 'ready'
    TERMINATING  = 'terminating'
    TERMINATED   = 'terminated'
    UNKNOWN      = 'unknown'

    def __str__(self):
        return self.value
