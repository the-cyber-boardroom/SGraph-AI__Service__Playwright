# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Safe_Str__Content_Proxy__Env__File
# Verbatim contents of a .env file shipped to the box. Permissive: tabs + newlines
# + printable ASCII (KEY=VALUE lines, secrets, comments). 32 KB cap (user-data
# bound). Whitespace preserved.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Content_Proxy__Env__File(Safe_Str):
    regex             = re.compile(r'^[\x09\x0a\x0d\x20-\x7e]*$')                   # tab, LF, CR, printable ASCII
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 32_768
    allow_empty       = True
    trim_whitespace   = False
