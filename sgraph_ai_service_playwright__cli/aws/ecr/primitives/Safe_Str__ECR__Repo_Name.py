# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — Safe_Str__ECR__Repo_Name
# ECR repository name. AWS rule: 2–256 chars, starts with lowercase letter or
# digit, then lowercase letters, digits, dots, underscores, slashes, hyphens.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECR__Repo_Name(Safe_Str):
    regex             = re.compile(r'^[a-z0-9][a-z0-9._/-]{1,255}$')             # ECR private-repo naming rule
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
