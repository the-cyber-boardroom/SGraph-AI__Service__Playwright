# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__AWS__Role__ARN
# Type-safe AWS IAM Role ARN string.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__Role__ARN(Safe_Str):
    max_length      = 256
    regex           = re.compile(r'[^a-zA-Z0-9:/\-_@.]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
