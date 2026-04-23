# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__AWS__Region
# AWS region code: two-letter area, dash, word, dash, digit. Examples:
# eu-west-2, us-east-1, ap-southeast-1. No partition prefix (aws-cn/aws-us-gov).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__AWS__Region(Safe_Str):
    regex             = re.compile(r'^[a-z]{2}-[a-z]+-\d+$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 32
    allow_empty       = True                                                        # Empty = "resolve from AWS_Config/env at runtime"
    to_lower_case     = True
    trim_whitespace   = True
