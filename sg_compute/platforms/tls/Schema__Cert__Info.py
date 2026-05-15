# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Cert__Info
# Decoded metadata for one X.509 certificate — the response shape of
# Cert__Inspector. Pure data, no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import List

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text   import Safe_Str__Text


class Schema__Cert__Info(Type_Safe):
    source             : str                             # 'file:/path' or 'host:1.2.3.4:443' — plain str: a path-sanitised primitive would mangle the '/'
    subject            : Safe_Str__Text
    issuer             : Safe_Str__Text
    serial             : Safe_Str__Text
    fingerprint_sha256 : Safe_Str__Text                  # hex, colon-separated
    sans               : List[str]                       # subjectAltName entries
    not_before         : int                             # unix ms
    not_after          : int                             # unix ms
    days_remaining     : int
    is_self_signed     : bool
    is_expired         : bool
