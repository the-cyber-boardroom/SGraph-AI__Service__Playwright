# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__Method
# HTTP request method as captured (GET, POST, …). Letters only; permissive so an
# odd attacker method is recorded rather than rejected.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__Method(Safe_Str):
    regex       = re.compile(r'[^A-Za-z]')                                          # letters only
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 16
