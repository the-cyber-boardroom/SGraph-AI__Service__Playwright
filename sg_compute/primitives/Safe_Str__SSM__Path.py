# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__SSM__Path
# AWS SSM Parameter Store path, e.g. "/sg-compute/nodes/my-node/api-key".
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__SSM__Path(Safe_Str):
    max_length        = 1024
    regex             = re.compile(r'^[a-zA-Z0-9/_.\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
