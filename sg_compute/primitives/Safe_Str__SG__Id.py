# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__SG__Id
# AWS Security Group ID, e.g. "sg-0123456789abcdef0". Empty = not yet assigned.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__SG__Id(Safe_Str):
    max_length        = 30
    regex             = re.compile(r'^sg-[0-9a-f]+$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
