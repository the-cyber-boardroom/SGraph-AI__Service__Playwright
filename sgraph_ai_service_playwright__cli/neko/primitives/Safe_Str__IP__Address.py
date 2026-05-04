# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__IP__Address (neko-local copy)
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__IP__Address(Safe_Str):
    regex             = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 15
    allow_empty       = True
    trim_whitespace   = True
