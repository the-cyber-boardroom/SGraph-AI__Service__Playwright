# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__AWS__Account_Id
# AWS account identifier: 12 decimal digits.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__Account_Id(Safe_Str):
    regex             = re.compile(r'^\d{12}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 12
    allow_empty       = True
    trim_whitespace   = True
