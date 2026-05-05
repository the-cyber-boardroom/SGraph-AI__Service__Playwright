# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Node__Name
# Operator-supplied or auto-generated node name.
# Pattern: lowercase letters, digits, hyphens; must start with a letter.
# Empty string allowed (triggers auto-generation in service layer).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Node__Name(Safe_Str):
    max_length        = 80
    regex             = re.compile(r'^[a-z][a-z0-9\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
