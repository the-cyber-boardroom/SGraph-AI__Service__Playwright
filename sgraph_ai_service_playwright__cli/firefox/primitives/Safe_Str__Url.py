# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Url
# URL string for Firefox profile start page. Allows all URL-legal characters.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Url(Safe_Str):
    max_length      = 2048
    regex           = re.compile(r'[\x00-\x1F\x7F ]')  # strip control chars and spaces
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
