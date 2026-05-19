# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — Safe_Str__EC2__AZ
# AWS Availability Zone identifier (e.g. eu-west-2a, us-east-1f, ap-northeast-1c).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__EC2__AZ(Safe_Str):
    regex             = re.compile(r'^[a-z]{2}-[a-z]+-\d[a-z]?$')               # e.g. eu-west-2a, ap-northeast-1c
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
