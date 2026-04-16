# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Step_Id primitive
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Step_Id(Safe_Str):                                                            # Per-step identifier within a sequence
    max_length  = 64                                                                # Caller may specify meaningful names
    regex       = re.compile(r'[^a-zA-Z0-9_\-.]')                                   # Alphanumerics + _ - .
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True                                                              # Steps without explicit IDs use index
