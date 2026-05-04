# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_UInt__Viewport_Dimension primitive
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt import Safe_UInt


class Safe_UInt__Viewport_Dimension(Safe_UInt):                                     # Browser viewport width/height
    min_value = 100
    max_value = 4096
