# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Action__Request (spec §5.9)
#
# Wrapper for direct Layer-0 action calls (POST /browser/click etc.).
# `step` is a dict on the wire — parsed by the dispatcher via STEP_SCHEMAS.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                         import Session_Id


class Schema__Action__Request(Type_Safe):                                           # Wrapper for direct action calls
    session_id              : Session_Id                                            # Must reference an active session
    step                    : dict                                                  # Single step dict; parsed by dispatcher
    capture_config          : Schema__Capture__Config = None                        # Override session-level config
    trace_id                : Safe_Str__Trace_Id = None
