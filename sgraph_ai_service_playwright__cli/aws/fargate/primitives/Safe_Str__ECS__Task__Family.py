# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/fargate — Safe_Str__ECS__Task__Family
# ECS task definition family name — alphanumeric, hyphens, underscores.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECS__Task__Family(Safe_Str):
    regex      = re.compile(r'[^A-Za-z0-9\-_]')
    regex_mode = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
