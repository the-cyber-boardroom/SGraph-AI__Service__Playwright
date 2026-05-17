# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Message
# Human-readable status / error message. Explicit regex preserves any printable
# ASCII plus common whitespace; without it the Safe_Str default would mangle
# every : = / % ( ) - the realistic message alphabet — same shape as the
# SignatureDoesNotMatch credential bug fixed on 2026-05-17.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Message(Safe_Str):
    max_length        = 512
    regex             = re.compile(r'[^\x20-\x7E\n\r\t]')   # printable ASCII + common whitespace
    regex_mode        = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty       = True
    strict_validation = False
