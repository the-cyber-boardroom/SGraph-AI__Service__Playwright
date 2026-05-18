# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Safe_Str__Lab__Entry_Id
# uuid4 hex — 32 lowercase hex chars, no dashes.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Lab__Entry_Id(Safe_Str):
    max_length  = 32
    regex       = re.compile(r'[^a-f0-9]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
