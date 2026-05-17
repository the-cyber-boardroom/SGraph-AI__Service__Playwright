# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__IAM__Role_Name
# IAM role name. AWS charset: alphanumeric + += , . @ _ - ; max 64 chars.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__IAM__Role_Name(Safe_Str):
    regex             = re.compile(r'^[a-zA-Z0-9+=,.@_\-]{1,64}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
