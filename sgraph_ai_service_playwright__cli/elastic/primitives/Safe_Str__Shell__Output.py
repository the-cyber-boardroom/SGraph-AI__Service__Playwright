# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Shell__Output
# Permissive string primitive for captured stdout / stderr from SSM Run Command.
# Shell output legitimately contains newlines, slashes, colons, equals signs,
# backticks, and any other punctuation — Safe_Str__Text would mangle it to
# unreadability. This primitive keeps the content intact up to a 1 MB cap;
# truncation beyond that is acceptable for the `sp elastic exec` diagnostic
# use case (switch to SSM S3 output if you ever need more).
#
# Case is preserved and whitespace is NOT trimmed — the whole point is fidelity.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


MAX_LENGTH = 1_000_000                                                              # 1 MB — generous; past that we should route via S3


class Safe_Str__Shell__Output(Safe_Str):
    regex             = re.compile(r'.*', re.DOTALL)                                # Anything incl. newlines; MATCH mode means the whole string must match, and .* always does
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True                                                        # Required by Safe_Str when regex_mode=MATCH; the regex is ".*" so nothing is actually rejected
    max_length        = MAX_LENGTH
    allow_empty       = True
    to_lower_case     = False
    trim_whitespace   = False
