# ═══════════════════════════════════════════════════════════════════════════════
# Schema__Agentic__Error — GET /admin/error response (v0.1.29)
#
# Last failed-load error string captured by the boot shim, if any. On a healthy
# container `has_error` is False and `error` is an empty string; in degraded
# mode `has_error` is True and `error` contains the formatted exception text.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous         import Safe_Str__Text__Dangerous


class Schema__Agentic__Error(Type_Safe):
    has_error : bool
    error     : Safe_Str__Text__Dangerous                                           # Multi-line traceback-style string; Dangerous variant preserves slashes / newlines-collapsed-to-spaces
