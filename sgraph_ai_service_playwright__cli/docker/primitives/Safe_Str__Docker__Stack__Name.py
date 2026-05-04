# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Docker__Stack__Name
# Logical name for an ephemeral Docker EC2 stack. Same regex as linux/opensearch
# equivalents.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Docker__Stack__Name(Safe_Str):
    regex             = re.compile(r'^[a-z][a-z0-9\-]{1,62}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 63
    allow_empty       = True
    to_lower_case     = True
    trim_whitespace   = True
