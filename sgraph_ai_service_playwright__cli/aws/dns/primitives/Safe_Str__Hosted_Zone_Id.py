# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Hosted_Zone_Id
# Route 53 hosted zone id. Accepts the bare form (Z + 1-32 alphanumeric chars)
# or the full ARN form (/hostedzone/Z…) — the prefix is stripped before
# validation so callers can pass either shape transparently.
# allow_empty=True for auto-init support; service code rejects empty on use.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                                 import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode         import Enum__Safe_Str__Regex_Mode


class Safe_Str__Hosted_Zone_Id(Safe_Str):
    regex             = re.compile(r'^Z[A-Z0-9]{1,32}$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    max_length        = 33                                                           # 'Z' + up to 32 alphanumeric chars
    allow_empty       = True                                                         # Auto-init support

    def __new__(cls, value='', **kwargs):                                             # Strip the /hostedzone/ prefix if present before validation
        if isinstance(value, str) and value.startswith('/hostedzone/'):
            value = value[len('/hostedzone/'):]
        return super().__new__(cls, value, **kwargs)
