# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Aws__Action
# IAM policy action string. Format: <service>:<action> where action may carry
# a trailing wildcard (*). Bare "*" is rejected — callers must use an explicit
# service-prefix (e.g. "iam:*"). This is the contract that prevents
# Action: "*" from being added to a Schema__IAM__Statement via the collection.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                             import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode    import Enum__Safe_Str__Regex_Mode


class Safe_Str__Aws__Action(Safe_Str):
    regex             = re.compile(r'^[a-zA-Z0-9\-]+:[a-zA-Z0-9*\-]+$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
