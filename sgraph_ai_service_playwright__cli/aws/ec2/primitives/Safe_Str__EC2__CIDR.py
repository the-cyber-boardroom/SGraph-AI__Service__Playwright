# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Safe_Str__EC2__CIDR
# IPv4 CIDR block (e.g. 10.0.0.0/16). Validated as dotted-quad / prefix-length.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__EC2__CIDR(Safe_Str):
    regex             = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
