# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__Origin_Id
# CloudFront origin identifier — alphanumeric + dash/underscore, max 128 chars.
# Must be unique within a distribution's origin list.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__Origin_Id(Safe_Str):
    regex             = re.compile(r'^[a-zA-Z0-9_\-]{1,128}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
    max_length        = 128
