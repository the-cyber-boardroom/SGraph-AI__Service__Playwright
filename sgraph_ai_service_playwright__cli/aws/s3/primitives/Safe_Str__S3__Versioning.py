# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/s3 — Safe_Str__S3__Versioning
# S3 versioning state (Enabled, Suspended, Disabled) — letters only.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3__Versioning(Safe_Str):
    regex      = re.compile(r'[^A-Za-z]')
    regex_mode = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
