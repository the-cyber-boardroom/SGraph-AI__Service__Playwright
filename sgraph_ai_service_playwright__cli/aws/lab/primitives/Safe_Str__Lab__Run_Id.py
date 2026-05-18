# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Safe_Str__Lab__Run_Id
# Pattern: <iso-ts-z>__<6-char nonce>
# Example: 2026-05-18T14:30:00Z__a1b2c3
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Lab__Run_Id(Safe_Str):
    max_length  = 32
    regex       = re.compile(r'[^a-zA-Z0-9T:Z_\-]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
