# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Content__Format
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content__Format(str, Enum):                                             # get_content return format
    HTML = "html"                                                                   # innerHTML
    TEXT = "text"                                                                   # innerText

    def __str__(self): return self.value
