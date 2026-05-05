# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Spec__Type_Id
# Type-safe spec type identifier (e.g. 'docker', 'firefox', 'vnc').
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Spec__Type_Id(Safe_Str):
    max_length  = 64
    regex       = re.compile(r'[^a-z0-9\-_]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True                          # default-constructible for Type_Safe fields
