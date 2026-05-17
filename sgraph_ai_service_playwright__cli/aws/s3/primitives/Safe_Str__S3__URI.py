# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__S3__URI
# Full S3 URI: s3://bucket or s3://bucket/key.
# Validates the s3:// scheme and bucket name; key portion is unconstrained.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__S3__URI(Safe_Str):
    regex             = re.compile(r'^s3://[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9](/.*)?$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
    max_length        = 2048

    def bucket(self) -> str:                                                          # parse bucket from s3://bucket/key
        s = str(self)
        if not s.startswith('s3://'):
            return ''
        rest = s[5:]
        return rest.split('/')[0]

    def key(self) -> str:                                                             # parse key from s3://bucket/key
        s = str(self)
        if not s.startswith('s3://'):
            return ''
        rest = s[5:]
        idx  = rest.find('/')
        if idx == -1:
            return ''
        return rest[idx + 1:]
