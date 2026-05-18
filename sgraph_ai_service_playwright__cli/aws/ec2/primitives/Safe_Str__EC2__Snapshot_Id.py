# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Safe_Str__EC2__Snapshot_Id
# EBS snapshot ID. AWS format: snap- followed by 8 or 17 hex characters.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__EC2__Snapshot_Id(Safe_Str):
    regex             = re.compile(r'^snap-[0-9a-f]{8,17}$')                     # AWS format: snap- + 8 or 17 hex; allow 8–17 to cover both old and new IDs
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
