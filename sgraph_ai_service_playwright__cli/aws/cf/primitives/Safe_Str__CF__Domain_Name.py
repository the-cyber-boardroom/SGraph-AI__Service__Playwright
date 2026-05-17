# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__Domain_Name
# CloudFront-assigned domain names (e.g. d1abcdef.cloudfront.net) and custom
# CNAME aliases (e.g. *.aws.sg-labs.app). Accepts optional leading wildcard.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__Domain_Name(Safe_Str):
    regex             = re.compile(
        r'^(\*\.)?[a-zA-Z0-9]([a-zA-Z0-9.\-]{0,251}[a-zA-Z0-9])?\.?$'
    )
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 255
    allow_empty       = True
    trim_whitespace   = True
