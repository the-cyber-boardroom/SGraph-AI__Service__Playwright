# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__IAM__Snapshot__Id
# Snapshot directory name. Format: <ISO-timestamp-Z>__<6-char-nonce>
# Example: 2026-05-17T12:34:56Z__a1b2c3
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__IAM__Snapshot__Id(Safe_Str):
    regex             = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z__[a-z0-9]{6}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
