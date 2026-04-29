# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Plugin__Stability
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Plugin__Stability(str, Enum):
    STABLE       = 'stable'
    EXPERIMENTAL = 'experimental'
    DEPRECATED   = 'deprecated'
