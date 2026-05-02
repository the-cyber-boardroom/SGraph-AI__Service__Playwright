# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Enum__Spec__Stability
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Spec__Stability(str, Enum):
    STABLE       = 'stable'
    EXPERIMENTAL = 'experimental'
    DEPRECATED   = 'deprecated'
