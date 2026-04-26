# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__Edge__Request__Id
# CloudFront edge request id — opaque ~52-char base64-ish identifier.
# Real example: "2TZI-f7L0PmDR-76lAEx4wdq-StamTTbisIdbMSYhB4eVeyTcPy0qw=="
# Char set: alphanumeric + - _ + / =  (URL-safe + base64 padding).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__Edge__Request__Id(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9_=+/\-]{1,128}$')                    # base64-ish + URL-safe variants
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 128
    allow_empty       = True
    trim_whitespace   = True
