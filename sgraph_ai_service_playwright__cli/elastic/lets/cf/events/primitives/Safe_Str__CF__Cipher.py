# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__Cipher
# TLS cipher suite name from ssl_cipher TSV column.
# Examples: "TLS_AES_128_GCM_SHA256", "ECDHE-RSA-AES128-GCM-SHA256".
# Char set: uppercase alphanumeric + underscore + hyphen.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__Cipher(Safe_Str):
    regex             = re.compile(r'^[A-Z0-9_\-]{1,64}$')                           # IANA-style cipher names — parser uppercases before construction
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 64
    allow_empty       = True
    trim_whitespace   = True
