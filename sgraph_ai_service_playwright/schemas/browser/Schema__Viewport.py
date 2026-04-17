# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Viewport (spec §5.2)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Viewport_Dimension          import Safe_UInt__Viewport_Dimension


class Schema__Viewport(Type_Safe):                                                  # Browser viewport dimensions
    width  : Safe_UInt__Viewport_Dimension = 1280
    height : Safe_UInt__Viewport_Dimension = 800
