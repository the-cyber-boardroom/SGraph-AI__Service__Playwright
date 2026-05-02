# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Safe_Str__Vnc__Password
# Operator password for the Caddy-fronted viewer. Single-quote safe only —
# user-data embeds value inside single-quoted shell variable.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vnc__Password(Safe_Str):
    regex             = re.compile(r'^[\x21-\x26\x28-\x7e]{4,128}$')               # Printable ASCII minus single quote
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 128
    allow_empty       = True
    trim_whitespace   = True
