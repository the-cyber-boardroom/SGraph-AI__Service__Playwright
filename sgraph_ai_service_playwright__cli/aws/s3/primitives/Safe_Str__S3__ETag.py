# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__S3__ETag
# S3 ETag value (hex MD5, optionally quoted, optionally with multipart suffix).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3__ETag(Safe_Str):
    regex             = re.compile(r'^"?[0-9a-fA-F]{32}(-[0-9]+)?"?$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
    max_length        = 72

    def unquoted(self) -> str:                                                        # strip surrounding quotes if present
        return str(self).strip('"')
