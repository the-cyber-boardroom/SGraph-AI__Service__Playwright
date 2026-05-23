# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__Reason
# Human-readable cause for a verdict, e.g. 'path never valid'. Spaces and common
# punctuation are preserved so the logged reason stays readable.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__Reason(Safe_Str):
    regex       = re.compile(r"[^a-zA-Z0-9 ._:/()\-]")                              # keep words + light punctuation
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 512
