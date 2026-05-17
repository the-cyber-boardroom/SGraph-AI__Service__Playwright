# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/observe — Safe_Str__Observe__Event_Time
# ISO-8601 timestamp of last observed event — printable ASCII only.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Observe__Event_Time(Safe_Str):
    regex      = re.compile(r'[^\x20-\x7E]')
    regex_mode = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
