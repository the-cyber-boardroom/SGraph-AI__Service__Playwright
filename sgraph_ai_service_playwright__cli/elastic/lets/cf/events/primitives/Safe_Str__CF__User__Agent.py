# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__User__Agent
# Request User-Agent string AFTER URL-decoding by Stage 1.
# Real example: "Mozilla/5.0 (compatible; wpbot/1.4; +https://forms.gle/...)"
# Char set is intentionally permissive — UAs in the wild contain almost
# anything printable.  Capped at 500 chars (Stage 1 truncates longer ones).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__User__Agent(Safe_Str):
    regex             = re.compile(r'^[\x20-\x7E]{0,500}$')                           # Printable ASCII (space..tilde); 0-500 chars
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 500
    allow_empty       = True
    trim_whitespace   = True
