# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Host primitive
#
# osbot_utils does not expose a bare hostname type; define one locally for the
# proxy bypass list. Accepts DNS names and IPv4 addresses; strict full-match so
# malformed values are rejected outright.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


HOST_REGEX = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-.]*[a-zA-Z0-9])?$')               # DNS label / dotted host / IPv4


class Safe_Str__Host(Safe_Str):                                                     # Bare hostname or IPv4 (no scheme, no port)
    max_length        = 253                                                         # DNS RFC 1035 limit
    regex             = HOST_REGEX
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True                                                        # Default-constructible for Type_Safe fields
    trim_whitespace   = True
