# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Stack__Id
# Type-safe stack identifier. Allows '_shared' for spec-wide blobs (all nodes),
# plus the normal stack-name pattern (lowercase alphanumeric, hyphens, underscores).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Stack__Id(Safe_Str):
    max_length  = 128
    regex       = re.compile(r'[^a-z0-9\-_]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
