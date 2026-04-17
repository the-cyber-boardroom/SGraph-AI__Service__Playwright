# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__Create__Response (spec §5.5)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.service.Schema__Service__Capabilities                     import Schema__Service__Capabilities
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                             import Schema__Session__Info


class Schema__Session__Create__Response(Type_Safe):                                 # POST /session/create response
    session_info            : Schema__Session__Info
    capabilities            : Schema__Service__Capabilities                         # Echo so caller knows constraints
