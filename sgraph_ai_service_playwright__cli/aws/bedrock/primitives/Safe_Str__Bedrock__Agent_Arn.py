# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Bedrock__Agent_Arn
# Bedrock AgentCore agent ARN — must look like an AWS ARN.
# Allow empty so default-constructed schemas are valid before population.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__Bedrock__Agent_Arn(Safe_Str):
    regex             = re.compile(r'^(arn:aws[a-z\-]*:[a-z0-9\-]+:[a-z0-9\-]*:[0-9]*:[\w\-\/\:\.]{1,256})?$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
