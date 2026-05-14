# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Read_Key
# An SG/API read key. Public by design (the vault is intentionally public) but
# kept inside the resolution layer and never surfaced to the browser. Charset is
# provisional — open question #1 in the dev pack.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Read_Key(Safe_Str):
    max_length        = 256
    regex             = re.compile(r'^[A-Za-z0-9_\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
