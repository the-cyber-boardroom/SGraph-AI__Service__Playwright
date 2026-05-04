# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__Host
# Hostname from cs_host TSV column.  Example: "sgraph.ai", "www.example.com".
# RFC-952/1123-ish: lowercase alphanumeric, dots, hyphens; up to 253 chars.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__Host(Safe_Str):
    regex             = re.compile(r'^[a-z0-9][a-z0-9.\-]{0,251}[a-z0-9]$|^[a-z0-9]$') # First+last alphanumeric, middle allows .-; 1-253 chars
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 253
    allow_empty       = True
    to_lower_case     = True                                                         # Hostnames are case-insensitive
    trim_whitespace   = True
