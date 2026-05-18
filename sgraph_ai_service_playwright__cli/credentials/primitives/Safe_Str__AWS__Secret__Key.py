# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__AWS__Secret__Key
# Type-safe AWS secret access key.
#
# AWS secret keys use the base64 alphabet (A-Z, a-z, 0-9, /, +, =).
# The explicit regex below is REQUIRED — without it, the Safe_Str base default
# silently replaces /, +, = with _, producing a corrupted secret that fails
# every SigV4 signature with SignatureDoesNotMatch.
#
# __repr__ always returns '****' — secret keys must never appear in logs.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__Secret__Key(Safe_Str):
    max_length      = 64
    regex           = re.compile(r'[^A-Za-z0-9/+=]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True

    def __repr__(self):
        return '****'
