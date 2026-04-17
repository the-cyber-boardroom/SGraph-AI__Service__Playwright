# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Sequence__Response (spec §5.8)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt

from sgraph_ai_service_playwright.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sgraph_ai_service_playwright.schemas.enums.Enum__Sequence__Status                              import Enum__Sequence__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Sequence_Id                        import Sequence_Id
from sgraph_ai_service_playwright.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds
from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                             import Schema__Session__Info


class Schema__Sequence__Response(Type_Safe):                                        # POST /sequence/execute response
    sequence_id             : Sequence_Id
    trace_id                : Safe_Str__Trace_Id
    status                  : Enum__Sequence__Status
    total_duration_ms       : Safe_UInt__Milliseconds
    steps_total             : Safe_UInt
    steps_passed            : Safe_UInt
    steps_failed            : Safe_UInt
    steps_skipped           : Safe_UInt
    step_results            : List[Schema__Step__Result__Base]                      # Heterogeneous; actual type per action
    session_info            : Schema__Session__Info                                 # Session state after sequence (may be closed)
    artefacts               : List[Schema__Artefact__Ref]                           # Cumulative artefact list
