# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Action__Response (spec §5.9)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                         import Session_Id
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                             import Schema__Session__Info


class Schema__Action__Response(Type_Safe):                                          # Response from a direct Layer 0 action
    session_id              : Session_Id
    trace_id                : Safe_Str__Trace_Id
    step_result             : Schema__Step__Result__Base                            # Typed per action
    session_info            : Schema__Session__Info                                 # Session state after action
