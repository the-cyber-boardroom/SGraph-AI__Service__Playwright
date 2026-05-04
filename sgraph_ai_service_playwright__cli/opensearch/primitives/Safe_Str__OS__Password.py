# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__OS__Password
# Password for OpenSearch's built-in "admin" superuser. Generated with
# secrets.token_urlsafe so the character set is URL-safe base64 (A-Z, a-z, 0-9,
# '-', '_'). Returned once on create; never stored server-side beyond the
# instance's own opensearch.env file. Mirrors Safe_Str__Elastic__Password.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__OS__Password(Safe_Str):
    regex             = re.compile(r'^[A-Za-z0-9_\-]{16,64}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 64
    allow_empty       = True                                                        # Empty on Info schema; create response always non-empty
    trim_whitespace   = True
