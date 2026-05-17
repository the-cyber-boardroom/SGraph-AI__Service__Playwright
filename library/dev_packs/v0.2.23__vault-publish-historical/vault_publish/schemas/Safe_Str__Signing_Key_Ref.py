# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Signing_Key_Ref
# A reference to the public key used to verify a slug's provisioning manifest
# signature. Stored on the billing record. The key custody / signing scheme is
# open question #4 in the dev pack and owned by SG/Send.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Signing_Key_Ref(Safe_Str):
    max_length        = 256
    regex             = re.compile(r'^[A-Za-z0-9_\-:.]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
