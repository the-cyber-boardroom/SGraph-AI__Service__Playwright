# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__Request_Id
# Sentinel request id, assigned at L1 before any rule runs. Form: 'sn-' + token
# (CloudFront requestId when present, else a hex timestamp). Permissive but bounded.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__Request_Id(Safe_Str):
    regex       = re.compile(r'[^A-Za-z0-9_=\-]')                                    # keep token chars; replace anything else
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 100
