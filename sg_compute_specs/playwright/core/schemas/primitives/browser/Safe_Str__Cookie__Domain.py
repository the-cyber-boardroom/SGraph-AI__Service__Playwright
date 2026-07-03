# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Cookie__Domain primitive (set_cookie verb)
#
# Same shape as Safe_Str__Host (DNS name / IPv4, no scheme, no port) plus an
# OPTIONAL leading dot — cookie Domain attributes legitimately use the
# ".example.com" form to cover subdomains. Strict full-match.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


COOKIE_DOMAIN_REGEX = re.compile(r'^\.?[a-zA-Z0-9]([a-zA-Z0-9\-.]*[a-zA-Z0-9])?$')  # Optional leading dot + DNS label / dotted host / IPv4


class Safe_Str__Cookie__Domain(Safe_Str):                                           # Cookie Domain attribute (host, optionally dot-prefixed)
    max_length        = 254                                                         # DNS RFC 1035 limit + leading dot
    regex             = COOKIE_DOMAIN_REGEX
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True                                                        # Default-constructible for Type_Safe fields
    trim_whitespace   = True
