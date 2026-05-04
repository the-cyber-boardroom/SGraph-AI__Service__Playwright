# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Enum__Spec__Nav_Group
# Dashboard navigation group for a spec.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Spec__Nav_Group(str, Enum):
    BROWSERS     = 'browsers'
    DATA         = 'data'
    OBSERVABILITY= 'observability'
    STORAGE      = 'storage'
    AI           = 'ai'
    DEV          = 'dev'
    OTHER        = 'other'
