# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/fargate — Safe_Str__ECS__CPU
# ECS CPU units string (e.g. "256", "1024") — digits only.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECS__CPU(Safe_Str):
    regex      = re.compile(r'[^0-9]')
    regex_mode = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
