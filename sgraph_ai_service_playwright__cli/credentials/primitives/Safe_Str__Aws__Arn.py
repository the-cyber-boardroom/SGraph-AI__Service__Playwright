# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI credentials — Safe_Str__Aws__Arn
# AWS ARN string. Empty allowed (= static creds, no identity ARN).
# Non-empty values must start with 'arn:'. Allows alphanumeric, colon,
# slash, hyphen, underscore, dot, at-sign (covers all ARN forms).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Aws__Arn(Safe_Str):
    max_length  = 2048
    regex       = re.compile(r'[^a-zA-Z0-9:/_\-\.@]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True                                # empty = static creds / identity not resolved
