# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Safe_Str__Slug
# Validated slug primitive. Charset: [a-z0-9-]; max 63 chars (DNS label limit).
# Slug__Validator enforces additional business rules (no consecutive hyphens,
# no leading/trailing hyphens, reserved-word check).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str               import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Slug(Safe_Str):
    regex             = re.compile(r'^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$|^[a-z0-9]$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 63
    allow_empty       = True
    to_lower_case     = True
    trim_whitespace   = True
