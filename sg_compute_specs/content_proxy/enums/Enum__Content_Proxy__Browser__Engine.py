# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Enum__Content_Proxy__Browser__Engine
# Engine the interactive sg-playwright-vnc fleet autostarts (one per container —
# an env choice on the SAME image, not a different image). Values match
# sg-playwright's Enum__Browser__Name / SG_PLAYWRIGHT__AUTOSTART_BROWSER.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content_Proxy__Browser__Engine(str, Enum):
    CHROMIUM = 'chromium'
    FIREFOX  = 'firefox'

    def __str__(self): return self.value
