# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Stack__Name
# Observability stack identifier shared by AMP alias, OpenSearch domain name,
# and AMG workspace name. AWS OpenSearch domain names are the tightest constraint:
# lowercase letters / digits / hyphens, 3-28 chars, must start with a letter.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Stack__Name(Safe_Str):
    regex             = re.compile(r'^[a-z][a-z0-9\-]{2,27}$')                      # AWS OS domain-name rules (strictest of the three services)
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 28
    allow_empty       = True                                                        # Auto-init requires zero-arg construction; regex still rejects non-empty garbage
    to_lower_case     = True
    trim_whitespace   = True
