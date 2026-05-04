# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_UInt__Timeout_MS primitive
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt import Safe_UInt


class Safe_UInt__Timeout_MS(Safe_UInt):                                             # Per-step or per-request timeout
    min_value = 0
    max_value = 300_000                                                             # 5 min per step; sequences may chain
