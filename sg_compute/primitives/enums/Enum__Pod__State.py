# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Enum__Pod__State
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Pod__State(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    STOPPED = 'stopped'
    FAILED  = 'failed'
