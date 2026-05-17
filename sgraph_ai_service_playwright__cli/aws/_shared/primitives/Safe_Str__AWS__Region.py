# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Safe_Str__AWS__Region
# Canonical home — consolidates copies in ec2/primitives/ and
# credentials/primitives/ (those re-export from here via deprecation shims).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__Region(Safe_Str):
    max_length  = 32
    regex       = re.compile(r'[^a-z0-9\-]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
