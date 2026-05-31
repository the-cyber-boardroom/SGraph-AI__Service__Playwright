# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__Act__Request (Φ7)
#
# Body for POST /session/{id}/act. Same shape as Schema__Sequence__Request
# but without browser_config or credentials — those were locked in at
# /session/open. The steps run against the held page; state PERSISTS
# across calls (cookies, JS state, console buffer accumulation).
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.capture.Schema__Capture__Config                           import Schema__Capture__Config
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Config                         import Schema__Sequence__Config


class Schema__Session__Act__Request(Type_Safe):                                     # POST /session/{id}/act body
    capture_config  : Schema__Capture__Config       = None
    sequence_config : Schema__Sequence__Config      = None
    steps           : List[dict]                                                    # Same heterogeneous step format as /sequence/execute
    trace_id        : Safe_Str__Trace_Id            = None
