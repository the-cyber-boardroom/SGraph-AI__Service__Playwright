# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Log__Stream
# CloudWatch Logs log stream name.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                              import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode      import Enum__Safe_Str__Regex_Mode


class Safe_Str__Log__Stream(Safe_Str):
    regex             = re.compile(r'^[\w\-\.\[\]/:$ ]{1,512}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
    max_length        = 512
