# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__JS__Expression primitive
#
# Accepts any JS string up to 4 KB; the dispatcher validates against a
# configured allowlist and rejects on mismatch. Security gating is NOT at the
# primitive level.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


ANY_CHARS_REGEX = re.compile(r'.*', re.DOTALL)                                      # Matches anything including newlines


class Safe_Str__JS__Expression(Safe_Str):                                           # JS expression for page.evaluate()
    max_length        = 4096                                                        # Reasonable limit
    regex             = ANY_CHARS_REGEX                                             # Content validation at dispatcher level (allowlist)
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True                                                        # Default-constructible for Type_Safe fields
