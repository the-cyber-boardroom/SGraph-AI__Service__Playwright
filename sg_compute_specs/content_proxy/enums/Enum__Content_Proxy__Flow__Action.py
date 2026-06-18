# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Enum__Content_Proxy__Flow__Action
# What the interceptor did with a flow — derived from the x-proxy-* headers it
# stamps. One value per flow, surfaced in the TUI traffic screen.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Content_Proxy__Flow__Action(str, Enum):
    INJECTED = 'injected'                                                           # response body overridden (page + injected <script>)
    BLOCKED  = 'blocked'                                                            # request short-circuited with a block response
    CACHED   = 'cached'                                                             # answered in the request phase (x-proxy-cached-in-request)
    SKIPPED  = 'skipped'                                                            # static asset / non-html — never sent to FastAPI
    FALLBACK = 'fallback'                                                           # FastAPI unreachable — flow passed through unchanged
    PASSED   = 'passed'                                                             # processed by FastAPI but no modification applied
