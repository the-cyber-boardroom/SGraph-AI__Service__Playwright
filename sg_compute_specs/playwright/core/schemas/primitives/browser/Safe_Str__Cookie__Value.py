# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Cookie__Value primitive (set_cookie verb)
#
# RFC 6265 cookie-value = *cookie-octet where cookie-octet is printable US-ASCII
# excluding control chars, whitespace, DQUOTE, comma, semicolon and backslash:
#   %x21 / %x23-2B / %x2D-3A / %x3C-5B / %x5D-7E
# Covers base64 / JWT-style values (+ / = . - _). Strict full-match — a value the
# jar could not round-trip is rejected outright, never silently mangled.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


COOKIE_VALUE_REGEX = re.compile(r'^[\x21\x23-\x2B\x2D-\x3A\x3C-\x5B\x5D-\x7E]*$')   # RFC 6265 cookie-octet set


class Safe_Str__Cookie__Value(Safe_Str):                                            # Cookie value (RFC 6265 cookie-octets)
    max_length        = 4096
    regex             = COOKIE_VALUE_REGEX
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True                                                        # Default-constructible; RFC 6265 also allows an empty value
    trim_whitespace   = True
