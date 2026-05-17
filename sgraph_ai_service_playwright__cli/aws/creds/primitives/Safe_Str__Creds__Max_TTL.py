# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Safe_Str__Creds__Max_TTL
# TTL string like '1h', '30m', '3600' (alphanumeric only).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Creds__Max_TTL(Safe_Str):
    regex       = re.compile(r'[^A-Za-z0-9]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
