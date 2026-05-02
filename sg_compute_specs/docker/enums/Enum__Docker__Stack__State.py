# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Enum__Docker__Stack__State
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Docker__Stack__State(Enum):
    PENDING     = 'pending'
    RUNNING     = 'running'
    STOPPING    = 'stopping'
    STOPPED     = 'stopped'
    TERMINATING = 'terminating'
    TERMINATED  = 'terminated'
    UNKNOWN     = 'unknown'
