# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Slug
# Type guarantee that a value looks like a slug: lowercase letters, digits and
# hyphens only, max 40 chars. The full naming rules (length floor, leading /
# trailing / double hyphen, reserved, profanity) live in Slug__Validator — that
# class is the single place slug policy is decided. This type is the floor.
# Empty is allowed so response schemas can default-construct; Slug__Validator
# rejects empty as TOO_SHORT.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Slug(Safe_Str):
    max_length        = 40
    regex             = re.compile(r'^[a-z0-9\-]+$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
