# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__Referer
# Referer header value AFTER Stage 1 has stripped the query string portion.
# Examples: "https://example.com/", "https://google.com/search".
# Permissive printable-ASCII char set; capped at 1024 chars.  CloudFront
# emits "-" when missing — parser maps to empty.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__Referer(Safe_Str):
    regex             = re.compile(r'^[\x20-\x7E]{0,1024}$')                          # Printable ASCII; query-stripped by Stage 1
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 1024
    allow_empty       = True
    trim_whitespace   = True
