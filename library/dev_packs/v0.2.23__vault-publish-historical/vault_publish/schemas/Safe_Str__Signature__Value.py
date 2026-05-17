# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Signature__Value
# The signature value over a provisioning manifest. Opaque token; the concrete
# encoding depends on the signing scheme (open question #4, owned by SG/Send).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Signature__Value(Safe_Str):
    max_length        = 1024
    regex             = re.compile(r'^[A-Za-z0-9_\-=+/]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
