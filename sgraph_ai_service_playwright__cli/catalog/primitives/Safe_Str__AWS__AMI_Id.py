# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__AWS__AMI_Id
# Type-safe AWS AMI identifier (e.g. 'ami-0123456789abcdef0').
# Allows lowercase alphanumeric and hyphens.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__AMI_Id(Safe_Str):
    max_length      = 24
    regex           = re.compile(r'[^a-z0-9\-]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True                           # empty = not specified; validator checks per creation_mode
