# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Safe_Str__Tui_Api__Capability
# A capability verb within an API scope, e.g. 'read' | 'write' | 'list_objects'.
# '*' is allowed and means "all methods of the API" (the coarse whole-API grant).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Tui_Api__Capability(Safe_Str):
    regex       = re.compile(r'[^a-z0-9_*-]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    max_length  = 64
    allow_empty = True
