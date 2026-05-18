# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Safe_Str__AWS__Account_Id
# Canonical home — consolidates copies in credentials/primitives/.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__Account_Id(Safe_Str):
    max_length  = 12
    regex       = re.compile(r'[^0-9]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
