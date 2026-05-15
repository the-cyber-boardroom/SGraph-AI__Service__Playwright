# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Int__TTL
# DNS TTL value in seconds. Route 53 enforces 1 to 2147483647 (signed 32-bit
# int max). Default is 300 (5 minutes). Aliases have no TTL — callers use 0
# as a sentinel in that context; the 0 alias sentinel is handled by callers,
# this primitive covers the full non-alias range (1 to 2147483647).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_Int                                  import Safe_Int


class Safe_Int__TTL(Safe_Int):
    min_value     = 1                                                                  # Route 53 minimum TTL for non-alias records
    max_value     = 2147483647                                                         # Route 53 maximum TTL (signed 32-bit int max)

    @classmethod
    def __default__value__(cls):                                                       # Called by Safe_Int.__new__ when value is None and min_value > 0
        return 300                                                                     # 5-minute default — sensible for most operator use
