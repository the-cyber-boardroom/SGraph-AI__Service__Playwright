# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__Name
# Human-facing label (e.g. a rule name like 'wp-scan-on-static'). Hyphens, spaces
# and dots are preserved so the label reads as written.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__Name(Safe_Str):
    regex       = re.compile(r'[^a-zA-Z0-9 ._\-]')                                  # keep words + hyphen/space/dot
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 128
