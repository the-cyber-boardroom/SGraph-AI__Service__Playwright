# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Safe_Str__EC2__Instance__Type
# EC2 instance type string, e.g. 't3.micro', 'm5.large', 't4g.nano'.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__EC2__Instance__Type(Safe_Str):
    regex             = re.compile(r'^[a-z][a-z0-9]*(\.[a-z0-9]+)*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
