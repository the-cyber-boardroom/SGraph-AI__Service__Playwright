# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Vault_Path primitive
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vault_Path(Safe_Str):                                               # Path within a vault
    max_length      = 1024                                                          # e.g. /sessions/openrouter/cookies.json
    regex           = re.compile(r'[^a-zA-Z0-9_\-./]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True                                                          # Default-constructible for Type_Safe fields
    trim_whitespace = True
