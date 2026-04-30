# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Firefox__Interceptor__Source
# Raw Python source for an inline mitmproxy interceptor. Operator passes the
# contents of a .py file at create time; embedded verbatim in EC2 user-data
# and written to /opt/sg-firefox/interceptors/active.py at boot.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Firefox__Interceptor__Source(Safe_Str):
    regex             = re.compile(r'^[\x09\x0a\x20-\x7e]*$')                       # Tabs + newlines + printable ASCII
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 32_768
    allow_empty       = True
    trim_whitespace   = False                                                        # Preserve indentation
