# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Step__Action (the declarative step vocabulary)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Step__Action(str, Enum):                                                # The declarative step vocabulary
    NAVIGATE       = "navigate"                                                     # Go to URL
    CLICK          = "click"                                                        # Click element
    FILL           = "fill"                                                         # Fill form field
    PRESS          = "press"                                                        # Press keyboard key
    SELECT         = "select"                                                       # Select option from dropdown
    HOVER          = "hover"                                                        # Mouse hover
    SCROLL         = "scroll"                                                       # Scroll viewport or element
    WAIT_FOR       = "wait_for"                                                     # Wait for selector / url / state
    SCREENSHOT     = "screenshot"                                                   # Capture screenshot
    VIDEO_START    = "video_start"                                                  # Begin session recording
    VIDEO_STOP     = "video_stop"                                                   # End session recording
    EVALUATE       = "evaluate"                                                     # Run JS expression (allowlist-gated)
    DISPATCH_EVENT = "dispatch_event"                                               # Synthetic DOM event
    SET_VIEWPORT   = "set_viewport"                                                 # Change viewport dimensions
    GET_CONTENT    = "get_content"                                                  # Return page HTML / text
    GET_URL        = "get_url"                                                      # Return current URL

    def __str__(self): return self.value
