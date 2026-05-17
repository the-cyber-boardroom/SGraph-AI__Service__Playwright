# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/cloudtrail — Safe_Str__CloudTrail__Username
# IAM username or assumed-role session name: permissive printable ASCII
# (can contain slashes, colons, etc. for assumed-role ARN-style usernames).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__CloudTrail__Username(Safe_Str):
    regex       = re.compile(r'[^\x20-\x7E]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
