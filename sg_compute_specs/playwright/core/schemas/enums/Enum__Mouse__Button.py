# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Mouse__Button
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Mouse__Button(str, Enum):                                               # Mouse button for click actions
    LEFT   = "left"
    RIGHT  = "right"
    MIDDLE = "middle"

    def __str__(self): return self.value
