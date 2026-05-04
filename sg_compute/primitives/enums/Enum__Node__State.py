# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Enum__Node__State
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Node__State(str, Enum):
    BOOTING     = 'booting'
    READY       = 'ready'
    TERMINATING = 'terminating'
    TERMINATED  = 'terminated'
    FAILED      = 'failed'
