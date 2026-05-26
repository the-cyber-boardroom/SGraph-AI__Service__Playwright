# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Journey__Result (one worker's terminal result)
#
# Adopts the qa-vault-app Schema__QA__Run__Result shape (renamed). Written into
# the vault at runs/.../workers/<run_id>/result.json by the worker. The full
# substrate sequence response is embedded verbatim; network_log_ref points at the
# per-run mitmproxy capture (slice 1).
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                    import Timestamp_Now
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                    import Safe_Str__Key

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Ref                             import Schema__Artefact__Ref
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Response                        import Schema__Sequence__Response
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Journey__Run__Status                         import Enum__Journey__Run__Status
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Journey_Id                       import Journey_Id
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Run_Id                           import Run_Id
from sg_compute_specs.user_journey.core.schemas.results.Schema__Journey__Assertion__Result               import Schema__Journey__Assertion__Result


class Schema__Journey__Result(Type_Safe):                                           # One journey run's terminal result
    run_id            : Run_Id                   = None                             # YYYY-MM-DDTHH-mm-ssZ__{journey_id}__{uuid8}
    journey_id        : Journey_Id               = None
    environment       : Safe_Str__Key            = None
    status            : Enum__Journey__Run__Status
    sequence_response : Schema__Sequence__Response = None                           # The substrate response, verbatim
    assertion_results : List[Schema__Journey__Assertion__Result]
    network_log_ref   : Schema__Artefact__Ref    = None                             # Populated from the per-run capture
    started_at        : Timestamp_Now            = None
    ended_at          : Timestamp_Now            = None
