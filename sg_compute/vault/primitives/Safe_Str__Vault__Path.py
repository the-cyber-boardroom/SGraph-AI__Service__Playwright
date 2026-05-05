# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Vault__Path
# Type-safe vault path within the per-spec namespace.
# e.g. 'spec/firefox/_shared/mitm-script'
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vault__Path(Safe_Str):
    max_length  = 512
    regex       = re.compile(r'[^a-zA-Z0-9_\-./]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
