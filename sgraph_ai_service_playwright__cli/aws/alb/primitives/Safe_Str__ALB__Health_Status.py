# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Safe_Str__ALB__Health_Status
# ALB target health status string. Lowercase alphanumeric and underscores.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ALB__Health_Status(Safe_Str):
    regex       = re.compile(r'[^a-z_]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
