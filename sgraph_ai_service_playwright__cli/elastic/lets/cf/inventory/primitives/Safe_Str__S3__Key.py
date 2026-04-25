# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__S3__Key
# Full S3 object key. AWS allows up to 1024 bytes of UTF-8; we restrict to a
# safe ASCII subset (alphanumerics + dot, hyphen, underscore, slash, colon,
# space, plus) which is enough for every Firehose-emitted CloudFront log key
# and most other operational uses without inviting weird-key edge cases.
# Use Safe_Str__S3__Key__Prefix when the value may be empty.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3__Key(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9._/:\-+ ]{1,1024}$')                 # ASCII-safe character set; 1-1024 chars (S3 key length cap)
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 1024
    allow_empty       = True                                                        # Auto-init support; service rejects empty on persist
    trim_whitespace   = False                                                       # S3 keys with leading/trailing spaces are technically valid; preserve verbatim
