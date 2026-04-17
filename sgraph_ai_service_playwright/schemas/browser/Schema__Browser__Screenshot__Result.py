# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Browser__Screenshot__Result (v0.1.24)
#
# Internal pairing of PNG bytes + timings for /browser/screenshot. The route
# emits png_bytes as the raw response body and timings as X-*-Ms headers —
# never serialised as JSON.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Timings                        import Schema__Sequence__Timings


class Schema__Browser__Screenshot__Result(Type_Safe):
    png_bytes : bytes
    timings   : Schema__Sequence__Timings
