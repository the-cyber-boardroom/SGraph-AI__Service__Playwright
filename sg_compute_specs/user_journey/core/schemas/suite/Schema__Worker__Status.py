# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Worker__Status (one worker's live state in a suite run)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                    import Timestamp_Now
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id                     import Safe_Str__Id

from sg_compute_specs.playwright.core.schemas.artefact.Schema__Artefact__Ref                             import Schema__Artefact__Ref
from sg_compute_specs.user_journey.core.schemas.enums.Enum__Worker__State                                import Enum__Worker__State
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Journey_Id                       import Journey_Id
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Run_Id                           import Run_Id
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Worker_Id                        import Worker_Id


class Schema__Worker__Status(Type_Safe):                                            # One worker's live state
    worker_id      : Worker_Id           = None
    run_id         : Run_Id              = None                                     # the journey run id (X-SG-Run-Id)
    journey_id     : Journey_Id          = None
    container_name : Safe_Str__Id        = None                                     # docker container/label
    state          : Enum__Worker__State
    exit_code      : Safe_UInt           = None                                     # container exit code when terminal
    result_ref     : Schema__Artefact__Ref = None                                   # pointer to runs/.../result.json
    started_at     : Timestamp_Now       = None
    finished_at    : Timestamp_Now       = None
