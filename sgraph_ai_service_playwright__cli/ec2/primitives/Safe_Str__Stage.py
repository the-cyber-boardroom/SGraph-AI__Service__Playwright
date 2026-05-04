# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Stage
# Deployment stage identifier. Lowercase letters / digits / hyphens.
# Typical values: "dev", "staging", "prod".
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Stage(Safe_Str):
    regex             = re.compile(r'^[a-z][a-z0-9\-]{0,31}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 32
    allow_empty       = True
    to_lower_case     = True
    trim_whitespace   = True
