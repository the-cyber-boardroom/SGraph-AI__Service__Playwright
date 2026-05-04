# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Schema__Interceptor__Source (GET /config/interceptor response)
#
# Returns the currently-loaded interceptor script source + metadata.
# Phase 1 is read-only; Phase 2 adds the PUT endpoint with persistence.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                         import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous      import Safe_Str__Text__Dangerous
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path            import Safe_Str__File__Path


class Schema__Interceptor__Source(Type_Safe):
    path       : Safe_Str__File__Path
    size_bytes : int
    source     : Safe_Str__Text__Dangerous                                           # Full file contents — Safe_Str__Text strips newlines + '#'; Dangerous variant preserves source code verbatim
