# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Sentinel__Layer
# Which layer produced a decision. The MVP decides only at L1.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Sentinel__Layer(str, Enum):
    L1 = 'L1'
    L2 = 'L2'
