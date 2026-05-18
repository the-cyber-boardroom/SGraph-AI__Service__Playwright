# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Safe_Str__Creds__Secret_Access_Key
# AWS secret access key (base64-like string).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Creds__Secret_Access_Key(Safe_Str):
    regex       = re.compile(r'[^A-Za-z0-9+/=\-_]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
