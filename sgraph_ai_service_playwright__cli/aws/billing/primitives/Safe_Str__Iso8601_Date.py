# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Iso8601_Date
# ISO 8601 calendar date in YYYY-MM-DD format. Validates shape only — no
# calendar logic (Feb 31 would pass). allow_empty = True for auto-init.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Iso8601_Date(Safe_Str):
    regex             = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 10
    allow_empty       = True
