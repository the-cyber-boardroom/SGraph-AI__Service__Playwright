# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ecr — Safe_Str__ECR__Image_Digest
# ECR image manifest digest. Always sha256:<64 hex chars>.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__ECR__Image_Digest(Safe_Str):
    regex             = re.compile(r'^sha256:[a-f0-9]{64}$')                     # OCI manifest digest format
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
