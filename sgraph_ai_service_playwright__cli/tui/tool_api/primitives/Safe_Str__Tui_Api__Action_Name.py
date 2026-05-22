# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Safe_Str__Tui_Api__Action_Name
# The invocable name of one action, e.g. 'list_objects' | 'vfs.read'.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Tui_Api__Action_Name(Safe_Str):
    regex       = re.compile(r'[^a-z0-9_.]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    max_length  = 64
    allow_empty = True
