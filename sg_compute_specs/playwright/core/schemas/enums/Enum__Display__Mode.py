# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Display__Mode
# How this instance renders browsers. HEADLESS is the base-image default (no X
# server in the container). VNC is baked into the sg-playwright-vnc image variant:
# Xvfb on :99 + noVNC on :6080 — headed launches render there and /desktop/browser
# is usable. Read from SG_PLAYWRIGHT__DISPLAY_MODE (Enum values = env values).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Display__Mode(str, Enum):                                               # How this instance renders browsers
    HEADLESS = 'headless'
    VNC      = 'vnc'

    def __str__(self): return self.value
