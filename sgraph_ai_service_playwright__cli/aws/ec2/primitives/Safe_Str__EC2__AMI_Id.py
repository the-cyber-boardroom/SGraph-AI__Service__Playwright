# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Safe_Str__EC2__AMI_Id
# EC2 AMI ID. AWS format: ami- followed by 8 or 17 hex characters.
# Also accepts alias strings (e.g. 'ubuntu-22.04-arm64') for the resolver.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__EC2__AMI_Id(Safe_Str):
    regex             = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-\.\_]{0,127}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
