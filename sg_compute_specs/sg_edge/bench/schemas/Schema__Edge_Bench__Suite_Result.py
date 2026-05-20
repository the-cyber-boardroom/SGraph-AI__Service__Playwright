# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Schema__Edge_Bench__Suite_Result
# The result of a bench run (one or many scenarios): the run id, target, the
# per-scenario results, and the overall pass flag. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Target                import Enum__Edge_Bench__Target
from sg_compute_specs.sg_edge.bench.schemas.List__Edge_Bench__Scenario_Result     import List__Edge_Bench__Scenario_Result


class Schema__Edge_Bench__Suite_Result(Type_Safe):
    run_id  : str
    target  : Enum__Edge_Bench__Target = Enum__Edge_Bench__Target.LOCAL
    results : List__Edge_Bench__Scenario_Result
    passed  : bool = True                                                            # all non-skipped scenarios passed
