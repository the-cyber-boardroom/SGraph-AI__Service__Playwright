# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__IAM__Policy_Name
# IAM policy name. Same charset as role names; max 128 chars.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__IAM__Policy_Name(Safe_Str):
    regex             = re.compile(r'^[a-zA-Z0-9+=,.@_\-]{1,128}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
