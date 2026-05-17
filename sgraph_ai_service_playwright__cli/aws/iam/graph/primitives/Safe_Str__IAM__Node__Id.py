# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__IAM__Node__Id
# Unique identifier for a graph node — typically the ARN or a synthetic ID.
# Accepts any non-empty string up to 2048 chars (ARN max is ~2048).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__IAM__Node__Id(Safe_Str):
    regex             = re.compile(r'^.{1,2048}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
