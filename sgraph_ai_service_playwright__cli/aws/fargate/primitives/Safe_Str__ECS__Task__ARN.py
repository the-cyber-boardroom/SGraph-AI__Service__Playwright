# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__ECS__Task__ARN
# ECS task ARN. Format: arn:aws:ecs:<region>:<account>:task/<cluster>/<id>
# or short form: arn:aws:ecs:<region>:<account>:task/<id>
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECS__Task__ARN(Safe_Str):
    regex             = re.compile(r'^arn:aws[a-z\-]*:ecs:[a-z0-9\-]+:\d{12}:task/[\w\-/]+$|^$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
