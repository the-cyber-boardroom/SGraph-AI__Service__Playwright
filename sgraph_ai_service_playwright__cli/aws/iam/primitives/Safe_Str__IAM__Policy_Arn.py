# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__IAM__Policy_Arn
# IAM managed policy ARN. Accepts both AWS-managed and customer-managed:
#   arn:aws:iam::aws:policy/<name>         (AWS managed)
#   arn:aws:iam::<account>:policy/<name>   (customer managed)
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__IAM__Policy_Arn(Safe_Str):
    regex             = re.compile(r'^arn:aws:iam::(\d{12}|aws):policy/.+$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
