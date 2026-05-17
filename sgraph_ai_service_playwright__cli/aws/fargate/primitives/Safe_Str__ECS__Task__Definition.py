# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__ECS__Task__Definition
# ECS task definition family:revision string, e.g. "my-task:3" or "my-task".
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECS__Task__Definition(Safe_Str):
    regex             = re.compile(r'^[a-zA-Z0-9\-_]+(?::\d+)?$|^$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
