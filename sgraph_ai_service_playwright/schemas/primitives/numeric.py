# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Numeric Primitives
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt import Safe_UInt


class Safe_UInt__Milliseconds(Safe_UInt):                                           # Any duration expressed in ms
    min_value = 0
    max_value = 900_000                                                             # 15 min — matches Lambda hard ceiling


class Safe_UInt__Timeout_MS(Safe_UInt):                                             # Per-step or per-request timeout
    min_value = 0
    max_value = 300_000                                                             # 5 min per step; sequences may chain


class Safe_UInt__Session_Lifetime_MS(Safe_UInt):                                    # How long a session may persist
    min_value = 0
    max_value = 14_400_000                                                          # 4 hours — sanity bound


class Safe_UInt__Viewport_Dimension(Safe_UInt):                                     # Browser viewport width/height
    min_value = 100
    max_value = 4096


class Safe_UInt__Memory_MB(Safe_UInt):                                              # Memory hint (informational)
    min_value = 128
    max_value = 30_720                                                              # Lambda max 10 GB; Fargate 30 GB
