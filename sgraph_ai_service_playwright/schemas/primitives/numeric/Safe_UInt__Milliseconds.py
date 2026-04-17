# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_UInt__Milliseconds primitive
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt import Safe_UInt


class Safe_UInt__Milliseconds(Safe_UInt):                                           # Any duration expressed in ms
    min_value = 0
    max_value = 900_000                                                             # 15 min — matches Lambda hard ceiling
