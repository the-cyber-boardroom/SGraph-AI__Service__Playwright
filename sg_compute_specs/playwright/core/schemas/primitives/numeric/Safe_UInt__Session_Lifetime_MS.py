# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_UInt__Session_Lifetime_MS primitive
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt import Safe_UInt


class Safe_UInt__Session_Lifetime_MS(Safe_UInt):                                    # How long a session may persist
    min_value = 0
    max_value = 14_400_000                                                          # 4 hours — sanity bound
