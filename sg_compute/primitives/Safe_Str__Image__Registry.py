# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Image__Registry
# Docker / ECR registry hostname, e.g. 123456789.dkr.ecr.eu-west-2.amazonaws.com
# Empty string is allowed (means no registry / local image).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Image__Registry(Safe_Str):
    max_length        = 255
    regex             = re.compile(r'^[a-zA-Z0-9._/:\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
