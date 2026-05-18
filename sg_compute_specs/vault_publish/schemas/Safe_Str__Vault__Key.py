# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Safe_Str__Vault__Key
# Vault key identifier. Alphanumeric + hyphens. Empty allowed for auto-init.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str               import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vault__Key(Safe_Str):
    regex             = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 128
    allow_empty       = True
    trim_whitespace   = True
