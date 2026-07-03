# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Version__Browser primitive (F1 — chromium 0.0.0)
#
# osbot-utils' Safe_Str__Version caps at 3 dot-segments of 1-3 digits each
# (^v?\d{1,3}(?:\.\d{1,3}){0,2}$, max_length 12). Real Chromium versions are
# 4 segments with a 4-digit build — e.g. "148.0.7778.96" — so even a correct
# probe could never be stored in that type; it always collapsed to the '0.0.0'
# fallback. This primitive accepts real browser version strings (Chromium,
# Firefox "150.0.2", WebKit "26.4") while staying strictly numeric-dotted.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


BROWSER_VERSION_REGEX = re.compile(r'^\d{1,4}(?:\.\d{1,5}){0,3}$')                   # 1-4 dot-segments, each up to 5 digits — covers Chromium build numbers


class Safe_Str__Version__Browser(Safe_Str):                                          # Browser engine version, e.g. "148.0.7778.96"
    max_length        = 32
    regex             = BROWSER_VERSION_REGEX
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True                                                         # Default-constructible for Type_Safe fields
