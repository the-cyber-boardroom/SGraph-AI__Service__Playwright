# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Safe_Str__Log__Content
# Arbitrary multi-line log text from a container or sidecar API. The explicit
# regex below preserves any printable-ASCII character plus common whitespace
# (\n \r \t). Without it, the Safe_Str default silently replaces every non-
# alphanumeric byte with `_`, mangling colons, parens, equals signs, slashes,
# etc. — same default-regex shape as the SignatureDoesNotMatch credential bug
# fixed on 2026-05-17 (de95ba60 / ed3fffbe). 1 MB cap guards memory.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Log__Content(Safe_Str):
    max_length        = 1048576   # 1 MB — generous cap for raw container log output
    regex             = re.compile(r'[^\x20-\x7E\n\r\t]')   # printable ASCII + common whitespace
    regex_mode        = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty       = True
    strict_validation = False
