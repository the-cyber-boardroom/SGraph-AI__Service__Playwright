# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Transfer_Id
# An SG/API Transfer-ID. Derived from a slug by Slug__Resolver. Charset / length
# is provisional — open question #1 in the dev pack (the SG/Send simple-token
# contract). Constrained here to hex-ish lowercase to keep it typed.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Transfer_Id(Safe_Str):
    max_length        = 128
    regex             = re.compile(r'^[a-z0-9\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
