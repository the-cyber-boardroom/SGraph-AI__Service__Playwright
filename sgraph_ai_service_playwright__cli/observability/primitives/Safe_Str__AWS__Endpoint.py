# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__AWS__Endpoint
# AWS service endpoint hostname (OpenSearch / AMP / AMG). Host-only (no scheme),
# since different services concatenate their own scheme/path fragments.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__Endpoint(Safe_Str):
    regex             = re.compile(r'^[a-z0-9][a-z0-9\-\.]*[a-z0-9]$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 253                                                         # RFC 1035 max hostname length
    allow_empty       = True                                                        # Missing during provisioning phase
    to_lower_case     = True
    trim_whitespace   = True
