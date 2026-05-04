# ═══════════════════════════════════════════════════════════════════════════════
# Schema__Agentic__Boot_Log — GET /admin/boot-log response (v0.1.29)
#
# First-pass: a bounded ring buffer of boot-shim log lines maintained in memory.
# Survives across warm invocations; empties on cold start. When the user app
# fails to import and the admin surface is serving in degraded mode, this
# endpoint is the first port of call — operators read the trail to find what
# broke without needing CloudWatch access.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                     import List

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text__Dangerous         import Safe_Str__Text__Dangerous


class Schema__Agentic__Boot_Log(Type_Safe):
    lines : List[Safe_Str__Text__Dangerous]                                         # Most-recent-last; bounded by BOOT_LOG_MAX_LINES in Agentic_Boot_State. Dangerous variant keeps slashes / colons from paths and tracebacks.
