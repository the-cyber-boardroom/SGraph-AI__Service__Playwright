# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__Keyring__Service_Name
# Type-safe keychain service name (e.g. 'sg.config.role.admin').
# Allows: lowercase alphanum, hyphens, dots, underscores.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Keyring__Service_Name(Safe_Str):
    max_length      = 512
    regex           = re.compile(r'[^a-z0-9\-._]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
