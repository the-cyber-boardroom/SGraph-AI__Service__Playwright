# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Safe_Str__EC2__Route_Table_Id
# Route Table ID. AWS format: rtb- followed by hex characters.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__EC2__Route_Table_Id(Safe_Str):
    regex             = re.compile(r'^rtb-[a-f0-9]+$')                          # AWS format: rtb- + hex
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
