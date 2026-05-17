# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI credentials — Safe_Str__Iso8601_Timestamp
# ISO 8601 UTC timestamp string. Pattern: YYYY-MM-DDTHH:MM:SSZ
# Allows digits, hyphens, colons, T, Z only. Empty = not yet set.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Iso8601_Timestamp(Safe_Str):
    max_length  = 24
    regex       = re.compile(r'[^0-9\-:TZ]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True                                # empty = not yet set / static creds have no expiry
