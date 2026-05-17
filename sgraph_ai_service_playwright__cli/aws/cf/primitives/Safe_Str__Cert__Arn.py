# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Cert__Arn
# ACM certificate ARN. Must be in us-east-1 for CloudFront.
# Example: 'arn:aws:acm:us-east-1:123456789012:certificate/abc-123'
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Cert__Arn(Safe_Str):
    regex             = re.compile(
        r'^arn:aws:acm:[a-z0-9-]+:\d{12}:certificate/[a-f0-9-]{36}$'
    )
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
