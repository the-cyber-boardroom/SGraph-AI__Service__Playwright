# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Manifest__Path
# A path inside the vault folder declared by the provisioning manifest — the
# content root, the health path, route content paths. Relative, forward-slash,
# no traversal segments (REPLACE mode strips disallowed characters).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Manifest__Path(Safe_Str):
    max_length  = 256
    regex       = re.compile(r'[^A-Za-z0-9_\-./]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
