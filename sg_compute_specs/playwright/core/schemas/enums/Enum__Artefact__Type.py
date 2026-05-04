# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Artefact__Type
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Artefact__Type(str, Enum):                                              # What kind of artefact
    SCREENSHOT   = "screenshot"
    VIDEO        = "video"
    PDF          = "pdf"
    HAR          = "har"                                                            # HTTP Archive
    TRACE        = "trace"                                                          # Playwright trace ZIP
    CONSOLE_LOG  = "console_log"
    NETWORK_LOG  = "network_log"
    PAGE_CONTENT = "page_content"                                                   # HTML snapshot

    def __str__(self): return self.value
