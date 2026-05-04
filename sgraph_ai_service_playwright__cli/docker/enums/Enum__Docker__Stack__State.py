# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Docker__Stack__State
# Lifecycle states for an ephemeral Docker EC2 stack.
# ═══════════════════════════════════════════════════════════════════════════════

from enum                                                                           import Enum


class Enum__Docker__Stack__State(Enum):
    PENDING     = 'pending'
    RUNNING     = 'running'
    STOPPING    = 'stopping'
    STOPPED     = 'stopped'
    TERMINATING = 'terminating'
    TERMINATED  = 'terminated'
    UNKNOWN     = 'unknown'
