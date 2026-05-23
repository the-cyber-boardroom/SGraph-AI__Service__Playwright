# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Safe_Str__Sentinel__IP
# Source IP. Holds an IPv4/IPv6 literal, or a hashed digest under privacy_mode='hash'
# (sha256 hex prefix), so the character set is hex digits, '.' and ':'.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from osbot_utils.type_safe.primitives.core.Safe_Str                         import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode import Enum__Safe_Str__Regex_Mode


class Safe_Str__Sentinel__IP(Safe_Str):
    regex       = re.compile(r'[^0-9a-fA-F.:]')                                     # ipv4 / ipv6 / hex digest
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
    max_length  = 45
