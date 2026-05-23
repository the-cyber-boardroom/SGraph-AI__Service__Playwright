# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__Timestamp
# ISO-8601 second-precision UTC timestamp, 'YYYY-MM-DDTHH:MM:SSZ', as L1 emits it.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__Timestamp(Safe_Str):
    regex       = re.compile(r'[^0-9T:Z\-]')                                        # iso-8601 second precision chars
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 32
