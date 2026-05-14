# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Safe_Str__Message
# Free-text message / detail field used in responses, URLs and provisioning
# steps. Keeps all printable ASCII; strips only control / non-printable bytes.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Message(Safe_Str):
    max_length  = 512
    regex       = re.compile(r'[^\x20-\x7E]')                                # strip only non-printable bytes
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
