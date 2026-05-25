# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__Text
# Free-text field (rule descriptions, confidence labels) that preserves ordinary
# sentence punctuation. Plain Safe_Str replaces spaces/'.'/';' with '_' — too
# aggressive for human-readable text — so this widens the allowed set.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__Text(Safe_Str):
    regex       = re.compile(r"[^a-zA-Z0-9 ._:/()\-,;'\"?!&+]")                      # words + ordinary punctuation
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 1024
