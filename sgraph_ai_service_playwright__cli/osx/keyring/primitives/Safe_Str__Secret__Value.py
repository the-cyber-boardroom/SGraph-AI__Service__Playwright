# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Safe_Str__Secret__Value
# Type-safe container for a secret string value (max 4 KB).
#
# Designed for generic secrets — AWS secret keys, PEM private keys, JWT
# tokens, base64 blobs, JSON config — so the allowed alphabet is the full
# printable-ASCII range plus common whitespace (\n \r \t). Without the
# explicit regex below, the Safe_Str base default silently replaces any
# non-alphanumeric character with `_`, which corrupts every base64-bearing
# secret (the SignatureDoesNotMatch bug fixed for Safe_Str__AWS__Secret__Key
# on 2026-05-17 had the same root cause).
#
# __repr__ returns '****' so the secret never appears in logs / tracebacks.
# __str__ deliberately returns the real value — callers like
# Sg__Aws__Session._make_base_session need it to construct boto3 sessions.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Secret__Value(Safe_Str):
    max_length      = 4096
    regex           = re.compile(r'[^\x20-\x7E\n\r\t]')      # strip only truly weird bytes; preserve printable ASCII + common whitespace
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True

    def __repr__(self):                                       # never leak the secret in logs / tracebacks
        return '****'
