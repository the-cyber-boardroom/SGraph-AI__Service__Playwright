# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Bedrock__Model_Id
# Bedrock model ID or inference-profile ARN.
# Accepts any non-empty string up to 256 chars (IDs vary widely by provider).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__Bedrock__Model_Id(Safe_Str):
    regex             = re.compile(r'^[\w\.\-\:\/]{1,256}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
