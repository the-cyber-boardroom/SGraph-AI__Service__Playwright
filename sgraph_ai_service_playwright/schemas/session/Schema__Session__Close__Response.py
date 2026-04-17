# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__Close__Response (spec §5.5)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                             import Schema__Session__Info


class Schema__Session__Close__Response(Type_Safe):                                  # DELETE /session/{id} response
    session_info            : Schema__Session__Info                                  # Final status
    artefacts               : List[Schema__Artefact__Ref]                           # All artefacts captured during session
    total_duration_ms       : Safe_UInt__Milliseconds
