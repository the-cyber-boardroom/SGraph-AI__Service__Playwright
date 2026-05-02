# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: Enum__Podman__Stack__State
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Podman__Stack__State(Enum):
    PENDING     = 'pending'
    RUNNING     = 'running'
    STOPPING    = 'stopping'
    STOPPED     = 'stopped'
    TERMINATING = 'terminating'
    TERMINATED  = 'terminated'
    UNKNOWN     = 'unknown'
