# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__SHA256
# Type-safe 64-character lowercase hex SHA-256 digest.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__SHA256(Safe_Str):
    max_length  = 64
    regex       = re.compile(r'[^a-f0-9]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
