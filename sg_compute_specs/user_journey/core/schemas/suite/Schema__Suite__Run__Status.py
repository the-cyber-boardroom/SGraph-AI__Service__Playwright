# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Suite__Run__Status (the conductor's live suite snapshot)
#
# What GET /suites/{id} returns and what the cockpit renders. `counts` and
# `aggregates` auto-initialise; `workers` is one entry per launched container.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                    import Timestamp_Now

from sg_compute_specs.user_journey.core.schemas.enums.Enum__Suite__Run__State                            import Enum__Suite__Run__State
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Suite_Id                         import Suite_Id
from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Suite_Run_Id                     import Suite_Run_Id
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Aggregates                         import Schema__Suite__Aggregates
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Counts                             import Schema__Suite__Counts
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Worker__Status                            import Schema__Worker__Status


class Schema__Suite__Run__Status(Type_Safe):                                        # The conductor's live suite snapshot
    suite_run_id : Suite_Run_Id = None
    suite_id     : Suite_Id     = None
    state        : Enum__Suite__Run__State
    counts       : Schema__Suite__Counts
    workers      : List[Schema__Worker__Status]
    aggregates   : Schema__Suite__Aggregates
    started_at   : Timestamp_Now = None
    ended_at     : Timestamp_Now = None
