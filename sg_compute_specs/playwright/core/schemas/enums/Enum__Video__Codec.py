# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Video__Codec
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Video__Codec(str, Enum):                                                # Video encoding
    WEBM = "webm"                                                                   # Playwright default; universal browser support
    MP4  = "mp4"                                                                    # Broader compatibility; requires transcode

    def __str__(self): return self.value
