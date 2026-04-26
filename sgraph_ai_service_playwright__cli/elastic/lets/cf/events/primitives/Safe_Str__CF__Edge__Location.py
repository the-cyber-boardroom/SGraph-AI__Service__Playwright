# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__Edge__Location
# CloudFront edge POP code, e.g. "HIO52-P4", "LHR62-P3", "DUB2-C1".
# Pattern: 2-4 alphanumeric region prefix, optional digits, hyphen, alphanumeric
# suffix.  We accept up to 16 chars to be generous against new POP code shapes.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__Edge__Location(Safe_Str):
    regex             = re.compile(r'^[A-Z0-9-]{2,16}$')                             # Uppercase alphanum + hyphen — parser uppercases before construction
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 16
    allow_empty       = True
    trim_whitespace   = True
