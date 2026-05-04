# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Health__Check (one health dimension, spec §5.1)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                         import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text                 import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key             import Safe_Str__Key


class Schema__Health__Check(Type_Safe):                                             # Individual health dimension
    check_name : Safe_Str__Key                                                      # e.g. "chromium_process"
    healthy    : bool
    detail     : Safe_Str__Text                                                     # Human-readable reason
