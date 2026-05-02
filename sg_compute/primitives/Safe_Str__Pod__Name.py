# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Pod__Name
# Container/pod name: lowercase letters, digits, underscores, hyphens.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Pod__Name(Safe_Str):
    max_length        = 63
    regex             = re.compile(r'^[a-z][a-z0-9_\-]{0,62}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
