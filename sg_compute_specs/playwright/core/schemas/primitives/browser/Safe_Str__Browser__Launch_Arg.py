# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Safe_Str__Browser__Launch_Arg primitive
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Browser__Launch_Arg(Safe_Str):                                      # Single chromium launch arg
    max_length  = 256
    regex       = re.compile(r'[^a-zA-Z0-9_\-=./:,*?@]')                            # Reasonable flag character set
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True                                                              # Default-constructible for Type_Safe fields
