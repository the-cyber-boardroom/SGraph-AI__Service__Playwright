# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI credentials — Safe_Str__Audit__Command_Args
# Redacted command args string for the audit log.
# No regex enforcement — printable ASCII only (control chars stripped).
# Values that are secrets must be replaced with <redacted> by the caller.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Audit__Command_Args(Safe_Str):
    max_length  = 2048
    regex       = re.compile(r'[^\x20-\x7E]')        # strip non-printable ASCII
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
