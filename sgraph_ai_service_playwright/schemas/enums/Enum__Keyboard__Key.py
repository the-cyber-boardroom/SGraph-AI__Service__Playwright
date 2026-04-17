# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Keyboard__Key
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Keyboard__Key(str, Enum):                                               # Common keyboard keys (extensible)
    ENTER       = "Enter"
    TAB         = "Tab"
    ESCAPE      = "Escape"
    BACKSPACE   = "Backspace"
    DELETE      = "Delete"
    ARROW_UP    = "ArrowUp"
    ARROW_DOWN  = "ArrowDown"
    ARROW_LEFT  = "ArrowLeft"
    ARROW_RIGHT = "ArrowRight"
    CONTROL_A   = "Control+a"
    CONTROL_C   = "Control+c"
    CONTROL_V   = "Control+v"

    def __str__(self): return self.value
