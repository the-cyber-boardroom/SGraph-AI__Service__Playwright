# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Instance__Id
# An EC2 instance id for a per-slug vault instance (e.g. 'i-0abc123...'). Empty
# string means no instance has been allocated for the slug yet.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Instance__Id(Safe_Str):
    max_length        = 32
    regex             = re.compile(r'^[a-z0-9\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
