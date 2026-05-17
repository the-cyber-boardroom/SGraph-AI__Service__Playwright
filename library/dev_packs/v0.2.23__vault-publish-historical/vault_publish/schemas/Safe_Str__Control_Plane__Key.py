# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Control_Plane__Key
# A random, single-use key the waker generates per provisioning run and delivers
# to the instance via IMDSv2. Never travels over a CloudFront-facing channel.
# URL-safe base64 alphabet, matching secrets.token_urlsafe() output.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Control_Plane__Key(Safe_Str):
    max_length        = 128
    regex             = re.compile(r'^[A-Za-z0-9_\-]*$')
    regex_mode        = Enum__Safe_Str__Regex_Mode.MATCH
    strict_validation = True
    allow_empty       = True
