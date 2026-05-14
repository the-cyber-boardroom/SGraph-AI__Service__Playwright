# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Vault_Path (playwright-local copy)
# Vault key or path. Allows the usual filesystem-path characters. Empty ok.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode     import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vault_Path(Safe_Str):
    max_length      = 1024
    regex           = re.compile(r'[^a-zA-Z0-9_\-./]')
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
    trim_whitespace = True
