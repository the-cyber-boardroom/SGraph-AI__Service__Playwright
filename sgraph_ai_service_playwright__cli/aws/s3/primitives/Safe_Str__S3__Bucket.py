# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__S3__Bucket
# S3 bucket name. DNS-compatible: 3-63 chars, lowercase alphanumeric + hyphens.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3__Bucket(Safe_Str):
    regex             = re.compile(r'^[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9]$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
    max_length        = 63
