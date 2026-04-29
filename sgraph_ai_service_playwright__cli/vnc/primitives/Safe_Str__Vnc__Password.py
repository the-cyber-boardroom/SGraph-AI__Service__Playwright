# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Vnc__Password
# Operator password for the nginx-fronted viewer + mitmproxy proxy auth.
# Used in two places:
#   - nginx htpasswd (bcrypt-hashed via `htpasswd -bcB`, so character set
#     doesn't matter to nginx itself)
#   - mitmproxy proxyauth file written as `operator:<password>` (standard
#     HTTP Basic auth, also tolerant)
#
# The only real constraint is the user-data shell embedding —
# `SG_VNC_OPERATOR_PASSWORD='{password}'` uses single-quote shell escaping,
# which has no escape interpretation, so any character is literal except
# single quote itself. Single quote is rejected here.
#
# Length: 4-128 chars. Auto-generated passwords (when omitted) are 32-char
# URL-safe base64 from secrets.token_urlsafe(24); operator-supplied passwords
# can be anything reasonable.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vnc__Password(Safe_Str):
    regex             = re.compile(r'^[\x21-\x26\x28-\x7e]{4,128}$')                # Printable ASCII (! through ~) minus single quote (0x27); 4-128 chars
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 128
    allow_empty       = True                                                        # Service rejects empty on create
    trim_whitespace   = True
