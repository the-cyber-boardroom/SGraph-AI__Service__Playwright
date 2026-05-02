# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Password__Write_Only
# Password field for credentials PUT. Never returned in GET responses.
# Accepts printable ASCII; control characters and null bytes are stripped.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Password__Write_Only(Safe_Str):
    max_length      = 128
    regex           = re.compile(r'[\x00-\x1F\x7F]')  # strip control chars only
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
