# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Suite__Definition (a suite: a list of fan-out entries)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Key                    import Safe_Str__Key

from sg_compute_specs.user_journey.core.schemas.primitives.identifiers.Suite_Id                         import Suite_Id
from sg_compute_specs.user_journey.core.schemas.suite.Schema__Suite__Entry                              import Schema__Suite__Entry


class Schema__Suite__Definition(Type_Safe):                                         # A suite the conductor runs
    suite_id : Suite_Id = None
    entries  : List[Schema__Suite__Entry]
    tags     : List[Safe_Str__Key]
