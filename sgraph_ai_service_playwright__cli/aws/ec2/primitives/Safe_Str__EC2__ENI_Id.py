# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Safe_Str__EC2__ENI_Id
# Elastic Network Interface ID. AWS format: eni- followed by 8 or 17 hex chars.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__EC2__ENI_Id(Safe_Str):
    regex             = re.compile(r'^eni-[0-9a-f]{8,17}$')                   # AWS format: eni- + 8 or 17 hex; allow 8–17 to cover old and new IDs
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
