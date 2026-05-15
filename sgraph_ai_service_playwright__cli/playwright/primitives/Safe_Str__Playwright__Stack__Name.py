# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Playwright__Stack__Name
# Logical name for an ephemeral Playwright FastAPI stack. Same regex shape as
# the vnc / elastic / opensearch / prometheus equivalents — sister sections
# share the naming shape so callers can swap.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Playwright__Stack__Name(Safe_Str):
    regex             = re.compile(r'^[a-z][a-z0-9\-]{1,62}$')                      # Letter start; 2-63 chars (matches docker container + tag naming comfort zone)
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 63
    allow_empty       = True                                                        # Service rejects empty on create
    to_lower_case     = True
    trim_whitespace   = True
