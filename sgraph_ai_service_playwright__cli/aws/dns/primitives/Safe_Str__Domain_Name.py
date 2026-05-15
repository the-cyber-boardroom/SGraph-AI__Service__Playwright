# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Domain_Name
# Fully-qualified or relative domain name. Accepts the dot-terminated form
# that Route 53 always appends (e.g. "sgraph.ai.") as well as plain names.
# Single-label names (e.g. "localhost") are accepted. Empty allowed for
# auto-init; service code rejects on actual use.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Domain_Name(Safe_Str):
    regex             = re.compile(                                                  # Multi-label or single label, optional trailing dot; leading * for wildcard certs (*.sgraph.ai)
        r'^(\*\.)?[a-zA-Z0-9]([a-zA-Z0-9.\-]{0,251}[a-zA-Z0-9])?\.?$'
    )
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 255                                                           # RFC 1035 limit including trailing dot
    allow_empty       = True                                                          # Auto-init support
    trim_whitespace   = True
