# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_UInt__Memory_MB primitive
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt import Safe_UInt


class Safe_UInt__Memory_MB(Safe_UInt):                                              # Memory hint (informational)
    min_value = 128
    max_value = 30_720                                                              # Lambda max 10 GB; Fargate 30 GB
