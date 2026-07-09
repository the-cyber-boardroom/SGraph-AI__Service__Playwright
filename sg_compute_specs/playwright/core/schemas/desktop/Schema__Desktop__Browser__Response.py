# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Desktop__Browser__Response
# Result of POST /desktop/browser. session_id is a REAL session — /session/{id}/
# act|probe|close all work against the same headed browser the user sees in noVNC.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.enums.Enum__Browser__Name                                 import Enum__Browser__Name
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Session_Id                          import Session_Id
from sg_compute_specs.playwright.core.schemas.primitives.text.Safe_Str__Url__Permissive                  import Safe_Str__Url__Permissive


class Schema__Desktop__Browser__Response(Type_Safe):                               # POST /desktop/browser result
    session_id    : Session_Id                                                     # drives /session/{id}/act|probe|close on the SAME visible browser
    engine        : Enum__Browser__Name = Enum__Browser__Name.CHROMIUM
    start_url     : Safe_Str__Url__Permissive = None                               # what was navigated to ('' / None → blank page)
    navigated     : bool = False                                                   # start_url given AND the navigate step succeeded
    expires_at_ms : int  = 0                                                       # epoch ms — session TTL (refreshed by /session activity)
