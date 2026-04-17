# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Quick__Screenshot__Result
#
# Internal return shape of Playwright__Service.quick_screenshot(). The raw PNG
# bytes are handed straight to the FastAPI route (which emits them as
# image/png), while `timings` travels alongside so the route can surface the
# per-phase wall-clock breakdown as HTTP headers (X-Playwright-Start-Ms,
# X-Browser-Launch-Ms, X-Steps-Ms, X-Browser-Close-Ms, X-Total-Ms).
#
# `png_bytes` is typed as `bytes` — the route consumes them directly; no
# Type_Safe primitive wraps raw binary.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Timings        import Schema__Sequence__Timings


class Schema__Quick__Screenshot__Result(Type_Safe):
    png_bytes : bytes                                                               # Raw PNG — decoded from the INLINE artefact's base64 payload
    timings   : Schema__Sequence__Timings                                           # Same per-phase breakdown as Schema__Quick__Html__Response, emitted via HTTP headers
