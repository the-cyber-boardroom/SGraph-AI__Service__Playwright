# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Safe_Str__Diagnostic
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


MAX_LENGTH = 4096


class Safe_Str__Diagnostic(Safe_Str):
    regex             = re.compile(r'^[\t\x20-\x7E\xA1-\xFF]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = MAX_LENGTH
    allow_empty       = True
    to_lower_case     = False
    trim_whitespace   = False
