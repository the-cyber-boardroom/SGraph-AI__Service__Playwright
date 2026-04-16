# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — S3 Primitives
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3_Key(Safe_Str):                                                   # S3 object key
    max_length      = 1024                                                          # AWS limit
    regex           = re.compile(r'[^a-zA-Z0-9_\-./]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True                                                          # Default-constructible for Type_Safe fields


class Safe_Str__S3_Bucket(Safe_Str):                                                # S3 bucket name
    max_length        = 63                                                          # AWS bucket limit
    regex             = re.compile(r'^[a-z0-9][a-z0-9\-.]*[a-z0-9]$')               # Full-match: lowercase alnum edges
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH                            # MATCH requires strict_validation=True
    strict_validation = True
    allow_empty       = True                                                        # Default-constructible for Type_Safe fields
