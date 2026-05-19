# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Safe_Str__ALB__Target_Type
# ALB target type string (instance, ip, lambda, alb). Lowercase only.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ALB__Target_Type(Safe_Str):
    regex       = re.compile(r'[^a-z]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
