# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__Country
# ISO-3166-1 alpha-2 country code (US, GB, DE, ...).  Two uppercase letters.
# CloudFront emits "-" when geo-IP is unavailable; the parser maps "-" to ''
# (empty allowed).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__Country(Safe_Str):
    regex             = re.compile(r'^[A-Z]{2}$')                                    # Strict A2 alpha; uppercase only — Stage 1 parser uppercases before construction
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 2
    allow_empty       = True
    trim_whitespace   = True
