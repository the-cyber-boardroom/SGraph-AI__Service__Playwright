# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__Audit__Detail
# Free-form human-readable audit detail line.
# Allows printable ASCII except control chars.
# Must NEVER contain secret values — caller is responsible for redacting.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Audit__Detail(Safe_Str):
    max_length      = 512
    regex           = re.compile(r'[^\x20-\x7E]')       # strip non-printable ASCII only
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
