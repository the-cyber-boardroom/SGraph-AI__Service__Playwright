# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Aws_Service_Code
# AWS service name string as returned by Cost Explorer (e.g.
# 'Amazon Elastic Compute Cloud - Compute', 'AWS Lambda',
# 'Amazon EC2 Container Registry (ECR)'). The default Safe_Str regex only
# allows alphanumerics and silently rewrites everything else to underscores,
# which produced unreadable display strings — set a permissive regex here.
# allow_empty = True supports auto-init and the 'OTHER' roll-up bucket.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Aws_Service_Code(Safe_Str):
    regex       = re.compile(r'[^A-Za-z0-9 \-().,/&_]')                                # REPLACE mode — anything outside this set becomes _
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    max_length  = 256
    allow_empty = True
