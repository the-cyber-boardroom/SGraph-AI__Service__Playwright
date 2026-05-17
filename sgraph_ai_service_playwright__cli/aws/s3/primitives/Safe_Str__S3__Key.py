# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__S3__Key
# S3 object key. Allows any printable character; max 1024 bytes per AWS docs.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3__Key(Safe_Str):
    regex             = re.compile(r'^[^\x00-\x1f\x7f]{0,1024}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
    max_length        = 1024
