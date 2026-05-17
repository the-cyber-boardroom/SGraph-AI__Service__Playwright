# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Lambda__Url
# Lambda Function URL. Format: https://<id>.lambda-url.<region>.on.aws/
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Lambda__Url(Safe_Str):
    regex             = re.compile(
        r'^https://[a-z0-9]+\.lambda-url\.[a-z0-9-]+\.on\.aws/$'
    )
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
