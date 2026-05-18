# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI credentials — Safe_Str__Sts__Session_Name
# STS session name. Pattern: [a-zA-Z0-9_=,.@-]{0,64}
# IAM SessionName is limited to 64 chars and these chars only.
# Empty = not yet resolved / static creds have no session name.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sts__Session_Name(Safe_Str):
    max_length  = 64
    regex       = re.compile(r'[^a-zA-Z0-9_=,.@\-]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True                                # empty = static creds / not yet resolved
