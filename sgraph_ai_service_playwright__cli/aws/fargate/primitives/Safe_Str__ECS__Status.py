# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/fargate — Safe_Str__ECS__Status
# ECS resource status string (ACTIVE, INACTIVE, RUNNING, STOPPED, etc.).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECS__Status(Safe_Str):
    regex      = re.compile(r'[^A-Z_]')
    regex_mode = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
