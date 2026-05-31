# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_UInt__Pixel__Dimension primitive
#
# Pixel width/height — covers artefact dimensions (full-page screenshots can
# be 20k+ px tall, well past the 4096 cap of Safe_UInt__Viewport_Dimension)
# and is sized for the absolute PNG spec ceiling (2^31-1) clamped to 16-bit
# unsigned (65_535) — large enough for every real-world capture, small
# enough to catch garbage from a corrupted IHDR chunk early.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.primitives.core.Safe_UInt import Safe_UInt


class Safe_UInt__Pixel__Dimension(Safe_UInt):                                       # Artefact / image pixel dimension
    min_value = 0
    max_value = 65_535
