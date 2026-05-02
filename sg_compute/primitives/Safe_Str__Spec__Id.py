# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Spec__Id
# Kebab-case spec identifier: starts with a letter, then lowercase letters,
# digits, underscores, or hyphens (max 63 chars total).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Spec__Id(Safe_Str):
    max_length        = 63
    regex             = re.compile(r'^[a-z][a-z0-9_\-]{0,62}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
