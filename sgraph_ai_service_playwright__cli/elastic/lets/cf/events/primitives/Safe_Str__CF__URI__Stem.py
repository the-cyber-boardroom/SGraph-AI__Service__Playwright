# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__URI__Stem
# Request URI path (cs_uri_stem column).  Examples: "/", "/enhancecp",
# "/robots.txt", "/api/v1/users/42".  No query string (CloudFront's realtime-
# log config strips that — and our Stage 1 cleaner double-checks).
# Char set: URL path safe characters per RFC 3986 unreserved + a few more
# practical ones.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__URI__Stem(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9._/~%\-+()&!*\':,@;=]{0,2048}$')      # RFC-3986-ish + practical unreserved set; URL-encoded chars (%xx) preserved
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 2048                                                         # Most browsers cap URLs around 2-4 KB
    allow_empty       = True
    trim_whitespace   = False                                                        # Leading/trailing slash matters
