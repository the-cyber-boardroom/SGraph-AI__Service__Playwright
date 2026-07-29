# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Desktop__Window__Mode
# How a headed /desktop/browser window sits on the VNC display (:99).
#   NORMAL    — default-sized window floating on the desktop (movable, resizable)
#   MAXIMISED — fills the display, keeps tabs + address bar (the useful default:
#               a 1920x1080 Xvfb with a 1280x720 window looks broken)
#   KIOSK     — fullscreen, NO tabs/address bar/decorations — pure content
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Desktop__Window__Mode(str, Enum):                                       # window geometry for a headed desktop browser
    NORMAL    = 'normal'
    MAXIMISED = 'maximised'
    KIOSK     = 'kiosk'

    def __str__(self): return self.value
