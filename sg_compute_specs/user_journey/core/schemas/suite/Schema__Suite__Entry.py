# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Suite__Entry (one fan-out line: image × journey × count)
#
# `count` workers of `worker_image` run `journey_id`, at most `concurrency` in
# flight. Raising count = more load. Per-worker env injection is finalized in the
# worker slice; the journey itself carries target_url + steps.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                    import Safe_Str__Key
from osbot_utils.type_safe.primitives.domains.numerical.safe_int.Safe_Int__Positive                 import Safe_Int__Positive

from sg_compute_specs.user_journey.core.schemas.primitives.docker.Safe_Str__Docker__Image               import Safe_Str__Docker__Image
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Journey_Id                       import Journey_Id


class Schema__Suite__Entry(Type_Safe):                                              # One fan-out line of a suite
    worker_image : Safe_Str__Docker__Image = None                                   # None → conductor's default runner image
    journey_id   : Journey_Id              = None                                   # Which journey in the vault
    environment  : Safe_Str__Key           = None                                   # dev | main | prod selector
    count        : Safe_Int__Positive      = 1                                      # How many copies → LOAD
    concurrency  : Safe_Int__Positive      = 1                                      # Max in flight at once
