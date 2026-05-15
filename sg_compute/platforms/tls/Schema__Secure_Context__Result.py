# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Secure_Context__Result
# What a browser reports back from the /tls/secure-context-check page: whether
# window.isSecureContext is true and whether the Web Crypto API is exposed.
# This is the actual pass/fail signal for the TLS PoC.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text   import Safe_Str__Text


class Schema__Secure_Context__Result(Type_Safe):
    url               : Safe_Str__Text
    user_agent        : Safe_Str__Text
    is_secure_context : bool
    has_web_crypto    : bool
    checked_at        : int                              # unix ms, browser-reported
