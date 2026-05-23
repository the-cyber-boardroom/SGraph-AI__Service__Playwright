# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__Host
# Request Host header value. Hostname chars plus an optional ':port'.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__Host(Safe_Str):
    regex       = re.compile(r'[^a-zA-Z0-9.:\-]')                                   # hostname + optional :port
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 255
