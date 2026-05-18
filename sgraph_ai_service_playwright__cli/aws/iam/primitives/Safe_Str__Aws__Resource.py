# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Aws__Resource
# IAM policy resource string. Accepts "*" (wildcard) or an ARN pattern,
# including ARNs with wildcard segments (e.g. arn:aws:ec2:*:*:instance/*).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__Aws__Resource(Safe_Str):
    regex             = re.compile(r'^(\*|arn:[a-zA-Z0-9\-*:./]+)$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
