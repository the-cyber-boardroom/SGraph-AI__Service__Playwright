# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__IP__Address
# IPv4 address string, e.g. "1.2.3.4". Empty = not yet assigned.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__IP__Address(Safe_Str):
    max_length        = 45                                                   # covers IPv4 + IPv6
    regex             = re.compile(r'^[0-9a-fA-F.:]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
