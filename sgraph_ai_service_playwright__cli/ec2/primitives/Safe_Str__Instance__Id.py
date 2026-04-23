# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Instance__Id
# Modern EC2 instance identifier: prefix "i-" + 17 hex chars. AWS has used the
# 17-char form since 2016 (older 8-char ids are phased out).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Instance__Id(Safe_Str):
    regex             = re.compile(r'^i-[0-9a-f]{17}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 19                                                          # "i-" + 17 hex
    allow_empty       = True                                                        # Auto-init support
    to_lower_case     = True
    trim_whitespace   = True
