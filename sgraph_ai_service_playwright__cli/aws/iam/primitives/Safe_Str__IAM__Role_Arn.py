# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__IAM__Role_Arn
# IAM role ARN. Format: arn:aws:iam::<account-id>:role/<name>
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__IAM__Role_Arn(Safe_Str):
    regex             = re.compile(r'^arn:aws:iam::\d{12}:role/.+$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
