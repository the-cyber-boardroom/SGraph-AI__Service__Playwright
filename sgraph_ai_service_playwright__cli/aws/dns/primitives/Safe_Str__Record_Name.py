# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Record_Name
# DNS record name within a hosted zone. Accepts multi-label RFC-1035 names,
# trailing dot, and a wildcard (*) at the first label. Route 53 always
# appends a trailing dot — both forms (with and without) are accepted.
# allow_empty=True for auto-init; service code rejects empty on use.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Record_Name(Safe_Str):
    regex             = re.compile(                                                   # Multi-label RFC-1035; wildcard * allowed at first label; trailing dot allowed
        r'^([a-zA-Z0-9_*]([a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?\.)*'
        r'[a-zA-Z0-9_*]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.?$'
    )
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 255                                                            # RFC 1035 limit including trailing dot
    allow_empty       = True                                                           # Auto-init support
    trim_whitespace   = True
