# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Safe_Str__Creds__Caller
# Caller identity — ARN, username, or userId (printable ASCII, permissive).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Creds__Caller(Safe_Str):
    regex       = re.compile(r'[^\x20-\x7E]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
