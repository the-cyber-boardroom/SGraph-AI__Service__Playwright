# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Safe_Str__Lab__Experiment_Name
# e.g. "propagation-timeline", "zone-inventory"
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Lab__Experiment_Name(Safe_Str):
    max_length  = 64
    regex       = re.compile(r'[^a-zA-Z0-9_\-]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
