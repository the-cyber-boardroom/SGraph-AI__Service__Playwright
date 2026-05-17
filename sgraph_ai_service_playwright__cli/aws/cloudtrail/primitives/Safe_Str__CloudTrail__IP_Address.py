# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/cloudtrail — Safe_Str__CloudTrail__IP_Address
# Source IP address: IPv4 dotted-decimal and IPv6 hex-colon notation.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__CloudTrail__IP_Address(Safe_Str):
    regex       = re.compile(r'[^0-9a-fA-F:.]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
