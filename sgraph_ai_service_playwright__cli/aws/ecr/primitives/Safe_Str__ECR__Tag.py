# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — Safe_Str__ECR__Tag
# ECR image tag. Docker rule: 1–128 chars, starts with [A-Za-z0-9_], then
# word chars, dots, dashes.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECR__Tag(Safe_Str):
    regex             = re.compile(r'^[\w][\w.-]{0,127}$')                       # Docker/OCI image tag rule
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
