# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__IP__Address
# Dotted-quad IPv4 address. Used for the caller's public IP (returned by
# Caller__IP__Detector) and to render SG ingress CIDRs as "{ip}/32".
# Regex accepts 0.0.0.0 through 255.255.255.255 loosely (full-range validation
# happens at the checkip.amazonaws.com fetch edge, not in the primitive).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__IP__Address(Safe_Str):
    regex             = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 15
    allow_empty       = True                                                        # Auto-init support
    trim_whitespace   = True
