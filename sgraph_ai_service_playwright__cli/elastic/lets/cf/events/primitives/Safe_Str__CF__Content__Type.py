# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__CF__Content__Type
# MIME type from sc_content_type TSV column.
# Examples: "text/html", "application/xml", "application/json; charset=utf-8".
# CloudFront emits "-" when the response carries no Content-Type header.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__CF__Content__Type(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9/.+\-=; *]{0,128}$')                  # MIME chars + parameters; "*" allowed for "*/*"
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 128
    allow_empty       = True
    to_lower_case     = True
    trim_whitespace   = True
