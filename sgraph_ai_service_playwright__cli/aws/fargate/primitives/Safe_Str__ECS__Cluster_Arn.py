# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/fargate — Safe_Str__ECS__Cluster_Arn
# ECS cluster ARN — printable ASCII characters only.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECS__Cluster_Arn(Safe_Str):
    regex      = re.compile(r'[^\x20-\x7E]')
    regex_mode = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
