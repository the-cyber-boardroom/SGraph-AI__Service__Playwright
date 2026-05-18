# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__AWS__Access__Key
# Type-safe AWS access key ID (AKIA… format).
# __repr__ returns '****' — access key IDs are sensitive.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__Access__Key(Safe_Str):
    max_length      = 32
    regex           = re.compile(r'[^A-Z0-9a-z]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True

    def __repr__(self):
        return '****'
