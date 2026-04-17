# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Selector primitive
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


ANY_CHARS_REGEX = re.compile(r'.*', re.DOTALL)                                      # Matches anything including newlines


class Safe_Str__Selector(Safe_Str):                                                 # CSS or XPath selector
    max_length        = 1024                                                        # Some frameworks emit long selectors
    regex             = ANY_CHARS_REGEX                                             # No content restriction — selectors use any chars
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True                                                        # MATCH mode needs strict_validation
    allow_empty       = True                                                        # Default-constructible for Type_Safe fields
    trim_whitespace   = True
