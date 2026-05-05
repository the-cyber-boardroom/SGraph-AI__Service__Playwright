# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Api__Key
# URL-safe base64 token from secrets.token_urlsafe(). Empty = not yet assigned.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Api__Key(Safe_Str):
    max_length        = 64
    regex             = re.compile(r'^[A-Za-z0-9_\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
