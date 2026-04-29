# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Vnc__Password
# Operator password for the nginx-fronted viewer + mitmproxy proxy auth.
# URL-safe base64 alphabet, 16-64 chars. Mirrors Safe_Str__OS__Password.
# Used for both:
#   - nginx Basic auth (operator-facing UI)
#   - MITM_PROXYAUTH on the mitmproxy container
# Both creds are rotated together; service generates one and uses it twice.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vnc__Password(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9_\-]{16,64}$')                      # URL-safe base64 alphabet; 16-64 chars
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 64
    allow_empty       = True                                                        # Service rejects empty on create
    trim_whitespace   = True
