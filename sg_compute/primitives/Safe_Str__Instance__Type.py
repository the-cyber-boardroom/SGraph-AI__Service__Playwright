# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Instance__Type
# EC2 instance type, e.g. "t3.medium", "m5.large". Empty = use default.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Instance__Type(Safe_Str):
    max_length        = 30
    regex             = re.compile(r'^[a-z][a-z0-9]+\.[a-z0-9]+$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
