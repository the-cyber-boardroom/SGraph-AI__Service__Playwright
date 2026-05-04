# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__One_Shot__Response (v0.1.24)
#
# Shared JSON response for the five JSON-returning /browser/* endpoints
# (navigate / click / fill / get-content / get-url). Screenshot returns raw
# image/png and emits these fields as X-*-Ms headers instead.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url                            import Safe_Str__Url

from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Page__Content                   import Safe_Str__Page__Content
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Timings                        import Schema__Sequence__Timings


class Schema__Browser__One_Shot__Response(Type_Safe):
    url         : Safe_Str__Url
    final_url   : Safe_Str__Url            = None                                   # Populated on navigate / click / get-url / get-content
    html        : Safe_Str__Page__Content  = None                                   # Populated only on /browser/get-content
    trace_id    : Safe_Str__Trace_Id
    duration_ms : Safe_UInt__Milliseconds
    timings     : Schema__Sequence__Timings                                         # Per-phase breakdown (same fields as /sequence/execute)
