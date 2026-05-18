# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI credentials — Safe_Str__Error__Message
# Free-form error message string.
# Allows any printable ASCII. Empty = no error / success.
# Must NEVER contain secret values — caller is responsible.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Error__Message(Safe_Str):
    max_length  = 2048
    regex       = re.compile(r'[^\x20-\x7E]')        # strip non-printable ASCII
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
