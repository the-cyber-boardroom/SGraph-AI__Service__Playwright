# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Node__Id
# Node identifier: {spec-id}-{adjective}-{noun}-{4-digits}
# e.g. firefox-quiet-fermi-7421
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Node__Id(Safe_Str):
    max_length        = 80
    regex             = re.compile(r'^[a-z][a-z0-9_\-]+$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
