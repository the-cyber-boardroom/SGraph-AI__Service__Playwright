# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Aws_Usage_Type
# AWS usage-type string as returned by Cost Explorer (e.g.
# 'EU-BoxUsage:t3.micro'). The explicit regex preserves the realistic alphabet:
# alphanumerics plus `: - _ . /`. Without it the Safe_Str default mangles the
# colon and dot — same default-regex shape as the SignatureDoesNotMatch
# credential bug fixed on 2026-05-17.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Aws_Usage_Type(Safe_Str):
    max_length  = 256
    regex       = re.compile(r'[^A-Za-z0-9:\-_./]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
