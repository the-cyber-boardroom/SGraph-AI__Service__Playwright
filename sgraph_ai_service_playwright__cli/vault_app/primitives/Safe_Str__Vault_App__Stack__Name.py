# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Vault_App__Stack__Name
# Logical name for an ephemeral vault-app EC2 stack. Same regex as sister
# sections so callers can swap naming conventions uniformly.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vault_App__Stack__Name(Safe_Str):
    regex             = re.compile(r'^[a-z][a-z0-9\-]{1,62}$')                     # Letter start; 2-63 chars
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 63
    allow_empty       = True                                                        # Service rejects empty on create
    to_lower_case     = True
    trim_whitespace   = True
