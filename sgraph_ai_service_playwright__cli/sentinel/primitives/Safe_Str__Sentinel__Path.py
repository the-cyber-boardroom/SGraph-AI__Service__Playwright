# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__Path
# The request path/URI as L1 saw it. Captured for logging + replay, so RFC-3986
# path/query characters are preserved verbatim (incl. '..', '%', '?', '&').
# Never used as a filesystem path — sink keys are request-id based.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__Path(Safe_Str):
    regex       = re.compile(r"[^a-zA-Z0-9 ._~:/?#\[\]@!$&'()*+,;=%\-]")            # RFC-3986 path/query set
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 2048
