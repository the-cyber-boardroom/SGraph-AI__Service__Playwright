# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Sequence__Response (v0.1.24)
#
# Stateless response — no `session_info` block (sessions are internal trace
# identifiers only, not wire-visible resources).
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sg_compute_specs.playwright.core.schemas.enums.Enum__Sequence__Status                              import Enum__Sequence__Status
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Sequence_Id                        import Sequence_Id
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Timings                        import Schema__Sequence__Timings


class Schema__Sequence__Response(Type_Safe):                                        # POST /sequence/execute response
    sequence_id       : Sequence_Id
    trace_id          : Safe_Str__Trace_Id
    status            : Enum__Sequence__Status
    total_duration_ms : Safe_UInt__Milliseconds
    steps_total       : Safe_UInt
    steps_passed      : Safe_UInt
    steps_failed      : Safe_UInt
    steps_skipped     : Safe_UInt
    step_results      : List[Schema__Step__Result__Base]                            # Heterogeneous; actual type per action
    artefacts         : List[Schema__Artefact__Ref]                                 # Cumulative artefact list
    timings           : Schema__Sequence__Timings                                   # Per-phase wall-clock breakdown
