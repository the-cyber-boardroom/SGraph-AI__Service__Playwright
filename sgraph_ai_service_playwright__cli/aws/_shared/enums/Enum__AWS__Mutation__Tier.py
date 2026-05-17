# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Enum__AWS__Mutation__Tier
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__AWS__Mutation__Tier(str, Enum):
    READ_ONLY      = 'read-only'
    MUTATING_LOW   = 'mutating-low'
    MUTATING_HIGH  = 'mutating-high'
