# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Diagnostic
# Permissive string primitive for human-readable diagnostic text — error
# message bodies, hint lines, status messages — that legitimately contain:
#   - slashes  (AWS ARNs, paths)
#   - colons   (URLs, ARNs, time stamps, ratios)
#   - equals   (env vars, key=value pairs)
#   - braces / brackets / angles (JSON snippets, regex placeholders)
#   - backticks, parentheses, dots, hyphens
#   - the entire printable Latin-1 range
#
# Safe_Str__Text would mangle most of these into underscores. This primitive
# exists because the project's pattern is "no raw str/dict attrs" (CLAUDE.md
# §2): we still want a Safe_Str at the boundary, just one that preserves the
# fidelity of the message it's carrying. Single-line by intent — newlines are
# stripped (use Safe_Str__Shell__Output for multi-line shell capture).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


MAX_LENGTH = 4096                                                                   # Generous for one-line error/status text


class Safe_Str__Diagnostic(Safe_Str):
    regex             = re.compile(r'^[\t\x20-\x7E\xA1-\xFF]*$')                    # ASCII printable + Latin-1 supplement; tab allowed; NO newlines
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = MAX_LENGTH
    allow_empty       = True
    to_lower_case     = False
    trim_whitespace   = False
