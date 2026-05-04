# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Plugin__Name
# Lowercase identifier matching the plugin's folder name under
# sgraph_ai_service_playwright__cli/. Letters + digits + underscores only;
# must start with a letter; max 63 chars (aligns with EC2 tag limit).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Plugin__Name(Safe_Str):
    regex             = re.compile(r'^[a-z][a-z0-9_]{0,62}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 63
    allow_empty       = True
    to_lower_case     = True
