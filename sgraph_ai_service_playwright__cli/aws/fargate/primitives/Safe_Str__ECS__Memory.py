# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/fargate — Safe_Str__ECS__Memory
# ECS memory MiB string (e.g. "512", "2048") — digits only.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECS__Memory(Safe_Str):
    regex      = re.compile(r'[^0-9]')
    regex_mode = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
