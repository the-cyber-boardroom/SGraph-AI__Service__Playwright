# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__S3__Key__Prefix
# A subset of an S3 key used as a ListObjectsV2 prefix filter. Same character
# set as Safe_Str__S3__Key but allow_empty defaults true semantically (an
# empty prefix means "list the entire bucket"). Length cap matches S3 key.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3__Key__Prefix(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9._/:\-+ ]{0,1024}$')                 # 0-1024 chars (empty allowed at the regex level)
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 1024
    allow_empty       = True                                                        # Empty = "list the entire bucket"
    trim_whitespace   = False
