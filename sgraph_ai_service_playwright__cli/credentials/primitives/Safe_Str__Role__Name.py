# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__Role__Name
# Type-safe role identifier (e.g. 'admin', 'dev', 'readonly').
# Allows: lowercase alphanum and hyphens.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Role__Name(Safe_Str):
    max_length      = 64
    regex           = re.compile(r'[^a-z0-9\-_]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
