# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__AWS__Account_Id
# Type-safe AWS account ID — 12 digits. Stored alongside the role config so we
# don't have to hit STS get_caller_identity every time a caller needs it.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__Account_Id(Safe_Str):
    max_length      = 12
    regex           = re.compile(r'[^0-9]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
