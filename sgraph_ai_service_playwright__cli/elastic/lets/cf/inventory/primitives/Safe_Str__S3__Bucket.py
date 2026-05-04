# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__S3__Bucket
# S3 bucket name. AWS rules: 3-63 chars, lowercase letters / digits / hyphens
# / dots; must start and end with letter or digit. Consecutive hyphens are
# allowed (the SGraph buckets use the "{account}--{name}--{region}" pattern,
# e.g. "745506449035--sgraph-send-cf-logs--eu-west-2"). Consecutive dots are
# not allowed in real AWS but the regex permits them for inbound flexibility —
# AWS itself will reject if anyone tries to use one.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3__Bucket(Safe_Str):
    regex             = re.compile(r'^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$')           # 3-63 chars total; first/last alphanumeric; middle allows hyphens and dots
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 63
    allow_empty       = True                                                        # Auto-init support; service rejects empty on load
    to_lower_case     = True
    trim_whitespace   = True
