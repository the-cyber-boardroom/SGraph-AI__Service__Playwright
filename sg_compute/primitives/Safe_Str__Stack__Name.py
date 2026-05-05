# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Stack__Name
# Human-readable stack name, e.g. "docker-quiet-fermi". Same character
# constraints as Safe_Str__Node__Name; kept separate for semantic clarity.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Stack__Name(Safe_Str):
    max_length        = 80
    regex             = re.compile(r'^[a-z][a-z0-9\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
