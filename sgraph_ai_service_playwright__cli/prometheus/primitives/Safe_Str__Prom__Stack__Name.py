# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Prom__Stack__Name
# Logical name for an ephemeral Prometheus + cAdvisor + node-exporter stack.
# Same regex as Safe_Str__OS__Stack__Name / Safe_Str__Elastic__Stack__Name —
# sister sections share the naming shape so callers can swap.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Prom__Stack__Name(Safe_Str):
    regex             = re.compile(r'^[a-z][a-z0-9\-]{1,62}$')                      # Letter start; 2-63 chars (matches EC2 tag + SG naming comfort zone)
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 63
    allow_empty       = True                                                        # Service rejects empty on create; auto-init friendliness
    to_lower_case     = True
    trim_whitespace   = True
