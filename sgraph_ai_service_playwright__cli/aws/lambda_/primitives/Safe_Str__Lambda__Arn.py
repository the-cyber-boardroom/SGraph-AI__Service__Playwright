# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Lambda__Arn
# Lambda function ARN. Format: arn:aws:lambda:<region>:<account>:function:<name>
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Lambda__Arn(Safe_Str):
    regex             = re.compile(
        r'^arn:aws:lambda:[a-z0-9-]+:\d{12}:function:[a-zA-Z0-9_\-]{1,64}$'
    )
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
