# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Browser__Name
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Browser__Name(str, Enum):                                               # Which browser engine
    CHROMIUM = "chromium"
    FIREFOX  = "firefox"
    WEBKIT   = "webkit"

    def __str__(self): return self.value
