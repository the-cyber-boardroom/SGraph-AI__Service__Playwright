# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Safe_Str__Content_Proxy__Ref
# A permissive reference string: a local file path, an s3:// URI, or an sgit ref.
# Used for vault sources and operator-supplied CA cert/key paths. Allows the
# path / URI separators that Safe_Str__Text strips.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Content_Proxy__Ref(Safe_Str):
    regex             = re.compile(r'^[a-zA-Z0-9._/:@\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 512
    allow_empty       = True
    trim_whitespace   = True
