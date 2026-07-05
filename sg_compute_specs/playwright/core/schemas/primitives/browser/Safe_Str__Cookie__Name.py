# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Cookie__Name primitive (set_cookie verb)
#
# RFC 6265 cookie-name = token (RFC 2616 §2.2): US-ASCII letters/digits plus
# ! # $ % & ' * + - . ^ _ ` | ~  — no separators, no whitespace, no control chars.
# Strict full-match so a malformed name is rejected outright, never mangled.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


COOKIE_NAME_REGEX = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")                   # RFC 6265 token characters


class Safe_Str__Cookie__Name(Safe_Str):                                             # Cookie name (RFC 6265 token)
    max_length        = 256
    regex             = COOKIE_NAME_REGEX
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True                                                        # Default-constructible for Type_Safe fields; non-empty is enforced by Request__Validator
    trim_whitespace   = True
