# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Inspect__Response (Φ5 — probe-batch)
#
# The "snapshot-once, probe-many" result. Each probe carries its full
# Schema__Step__Result__Base (with the lifted verb-specific fields:
# content/url/text/html/dom_tree/accessibility_tree/return_value/return_type/
# console_log/network_failures populated as applicable). Caller looks up by
# their chosen probe name.
#
# diagnostics is populated only when the request asked for them
# (diagnostics_on_fail=True) AND at least one step failed. Shape:
#   { 'console_log': [...], 'network_failures': [...] }
# Cheap insurance for caller-side post-mortem.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import Dict, List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Ref                            import Schema__Artefact__Ref
from sg_compute_specs.playwright.core.schemas.enums.Enum__Engine                                        import Enum__Engine
from sg_compute_specs.playwright.core.schemas.enums.Enum__Sequence__Status                              import Enum__Sequence__Status
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sg_compute_specs.playwright.core.schemas.primitives.identifiers.Sequence_Id                        import Sequence_Id
from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Milliseconds                import Safe_UInt__Milliseconds
from sg_compute_specs.playwright.core.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Timings                        import Schema__Sequence__Timings


class Schema__Inspect__Response(Type_Safe):                                         # /inspect response body
    inspect_id        : Sequence_Id                                                 # Reuse sequence_id shape — same identifier semantics
    trace_id          : Safe_Str__Trace_Id
    status            : Enum__Sequence__Status                                      # completed | partial | failed
    engine            : Enum__Engine                = Enum__Engine.SYNC
    total_duration_ms : Safe_UInt__Milliseconds
    navigate_result   : Schema__Step__Result__Base  = None                          # The navigate step's result
    settle_results    : List[Schema__Step__Result__Base]                            # One per settle step (may be empty)
    probe_results     : Dict[str, Schema__Step__Result__Base]                       # name → result (lifted fields carry through)
    diagnostics       : Dict                        = None                          # {console_log, network_failures} — populated when diagnostics_on_fail=True AND at least one failure
    artefacts         : List[Schema__Artefact__Ref]                                 # End-of-sequence artefacts (console_log / network_log via capture_config)
    timings           : Schema__Sequence__Timings
