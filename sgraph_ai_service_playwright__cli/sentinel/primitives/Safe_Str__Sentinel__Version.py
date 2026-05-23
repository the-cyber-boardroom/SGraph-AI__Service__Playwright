# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__Version
# Dotted semantic version (e.g. '0.1.0') for the engine + ruleset. Digits and dots
# are preserved (plain Safe_Str would strip the dots to underscores).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__Version(Safe_Str):
    regex       = re.compile(r'[^0-9.\-]')                                          # digits, dots, hyphen (pre-release)
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 32
