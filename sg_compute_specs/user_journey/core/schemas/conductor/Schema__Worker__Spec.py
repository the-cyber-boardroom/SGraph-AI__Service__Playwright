# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Worker__Spec (a planned worker, pre-launch)
#
# What the Suite__Runner produces from a Schema__Suite__Entry: one spec per replica,
# carrying the resolved image + the run_id the conductor will launch with (and that
# the worker stamps as X-SG-Run-Id).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                    import Safe_Str__Key

from sg_compute_specs.user_journey.core.schemas.primitives.docker.Safe_Str__Docker__Image               import Safe_Str__Docker__Image
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Journey_Id                       import Journey_Id
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Run_Id                           import Run_Id
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Worker_Id                        import Worker_Id


class Schema__Worker__Spec(Type_Safe):                                              # one planned worker
    worker_id     : Worker_Id               = None
    run_id        : Run_Id                  = None                                  # becomes X-SG-Run-Id
    worker_image  : Safe_Str__Docker__Image = None                                  # resolved (entry image or conductor default)
    journey_id    : Journey_Id              = None
    environment   : Safe_Str__Key           = None
    replica_index : Safe_UInt
