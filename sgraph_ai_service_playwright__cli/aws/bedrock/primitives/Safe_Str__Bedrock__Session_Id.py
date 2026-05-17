# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Bedrock__Session_Id
# AgentCore session identifier — alphanumeric with hyphens, up to 128 chars.
# Allow empty so default-constructed schemas are valid.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__Bedrock__Session_Id(Safe_Str):
    regex             = re.compile(r'^[\w\-]{0,128}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
