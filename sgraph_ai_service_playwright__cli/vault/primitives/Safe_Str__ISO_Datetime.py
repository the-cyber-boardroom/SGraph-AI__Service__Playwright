# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__ISO_Datetime
# Type-safe ISO 8601 datetime string (e.g. '2026-05-02T14:32:00Z').
# Allows digits, dashes, colons, T, Z, +, dot — just enough for ISO 8601.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ISO_Datetime(Safe_Str):
    max_length      = 32
    regex           = re.compile(r'[^0-9\-:TZ+.]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
