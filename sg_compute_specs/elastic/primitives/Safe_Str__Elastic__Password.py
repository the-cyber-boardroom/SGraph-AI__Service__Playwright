# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Safe_Str__Elastic__Password
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Elastic__Password(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9_\-]{16,64}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 64
    allow_empty       = True
    trim_whitespace   = True
