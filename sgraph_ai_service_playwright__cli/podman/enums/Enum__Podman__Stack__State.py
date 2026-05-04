# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Podman__Stack__State
# Lifecycle states for an ephemeral Podman EC2 stack.
# ═══════════════════════════════════════════════════════════════════════════════

from enum                                                                           import Enum


class Enum__Podman__Stack__State(Enum):
    PENDING     = 'pending'
    RUNNING     = 'running'
    STOPPING    = 'stopping'
    STOPPED     = 'stopped'
    TERMINATING = 'terminating'
    TERMINATED  = 'terminated'
    UNKNOWN     = 'unknown'
