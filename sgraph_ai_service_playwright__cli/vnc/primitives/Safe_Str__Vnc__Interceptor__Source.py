# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Vnc__Interceptor__Source
# Raw Python source for an inline interceptor (per plan doc 6 N5). The
# operator passes the contents of a `.py` file at create time; the source is
# embedded verbatim in the EC2 user-data heredoc and written to
# /opt/interceptors/runtime/active.py at boot.
#
# Permissive on purpose — Python source can include almost any printable
# character. The 32 KB cap is the conservative outer bound on user-data
# (AWS limit is 16 KB after base64; mitmproxy interceptors stay well under
# that in practice).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vnc__Interceptor__Source(Safe_Str):
    regex             = re.compile(r'^[\x09\x0a\x20-\x7e]*$')                       # Tabs + newlines + printable ASCII; rejects unicode + control bytes
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 32_768
    allow_empty       = True
    trim_whitespace   = False                                                       # Preserve leading whitespace for code indentation
