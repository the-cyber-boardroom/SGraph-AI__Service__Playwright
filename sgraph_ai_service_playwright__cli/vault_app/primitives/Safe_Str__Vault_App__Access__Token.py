# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Vault_App__Access__Token
# The single stack-wide secret shared by sg-send-vault, the playwright
# service, and the host-plane. Set once at stack creation; not retrievable
# after the create response. Min 16 chars to prevent trivially weak tokens.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Vault_App__Access__Token(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9\-_]{16,128}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True                                                        # Service generates one when empty
    trim_whitespace   = True
