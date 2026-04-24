# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__AMI__Id
# Modern AMI identifier: prefix "ami-" + 17 hex chars.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__AMI__Id(Safe_Str):
    regex             = re.compile(r'^ami-[0-9a-f]{17}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 21                                                          # "ami-" + 17 hex
    allow_empty       = True
    to_lower_case     = True
    trim_whitespace   = True
