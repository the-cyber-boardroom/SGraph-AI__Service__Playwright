# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Wait__State
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Wait__State(str, Enum):                                                 # Page-load state for navigate/wait_for
    LOAD               = "load"                                                     # load event fired
    DOM_CONTENT_LOADED = "domcontentloaded"                                         # DOMContentLoaded event
    NETWORK_IDLE       = "networkidle"                                              # No network activity for 500ms

    def __str__(self): return self.value
