# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/cloudtrail — Safe_Str__CloudTrail__Json_Blob
# JSON-serialised string for request_parameters, response_elements, resources.
# Allows tabs, newlines, and all printable ASCII (any JSON-safe characters).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__CloudTrail__Json_Blob(Safe_Str):
    regex       = re.compile(r'[^\x09\x0A\x0D\x20-\x7E]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
