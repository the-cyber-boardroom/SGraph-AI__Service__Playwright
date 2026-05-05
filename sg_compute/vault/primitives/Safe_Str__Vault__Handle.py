# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Vault__Handle
# Type-safe slug identifying a vault blob within a spec+stack namespace.
# Allows: lowercase alphanumeric, hyphens, dots (e.g. 'credentials',
# 'mitm-script', 'profile.tar.gz').
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vault__Handle(Safe_Str):
    max_length  = 128
    regex       = re.compile(r'[^a-z0-9\-.]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
