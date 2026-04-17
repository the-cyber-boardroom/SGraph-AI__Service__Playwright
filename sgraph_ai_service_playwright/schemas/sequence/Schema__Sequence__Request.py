# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Sequence__Request (spec §5.8)
#
# `steps` is List[dict] on the wire — the Sequence__Dispatcher parses each
# entry via STEP_SCHEMAS (§8) based on the `action` discriminator.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sgraph_ai_service_playwright.schemas.browser.Schema__Browser__Config                           import Schema__Browser__Config
from sgraph_ai_service_playwright.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Sequence_Id                        import Sequence_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                         import Session_Id
from sgraph_ai_service_playwright.schemas.sequence.Schema__Sequence__Config                         import Schema__Sequence__Config
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Credentials                      import Schema__Session__Credentials


class Schema__Sequence__Request(Type_Safe):                                         # POST /sequence/execute body
    sequence_id             : Sequence_Id = None                                    # Auto-generated if omitted
    session_id              : Session_Id  = None                                    # If set: run in existing session
    browser_config          : Schema__Browser__Config     = None                   # If session_id=None: create ad-hoc session
    credentials             : Schema__Session__Credentials = None                   # Ad-hoc session credentials
    capture_config          : Schema__Capture__Config
    sequence_config         : Schema__Sequence__Config
    steps                   : List[dict]                                            # Heterogeneous; parsed by dispatcher via STEP_SCHEMAS
    trace_id                : Safe_Str__Trace_Id = None
    close_session_after     : bool = True                                           # Tear down after sequence
