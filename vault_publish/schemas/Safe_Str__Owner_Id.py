# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Owner_Id
# Identifies the owner a slug is bound to in the billing record. The billing
# record itself is owned by SG/Send (open question #2 in the dev pack); this
# type is the local representation of the owner reference.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Owner_Id(Safe_Str):
    max_length        = 128
    regex             = re.compile(r'^[A-Za-z0-9_\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
