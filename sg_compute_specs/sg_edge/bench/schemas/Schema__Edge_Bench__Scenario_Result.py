# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Schema__Edge_Bench__Scenario_Result
# Outcome of running one scenario N times: its metrics (one per measured duration),
# overall pass/fail, and skip/error note. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Tier           import Enum__Edge_Bench__Tier
from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Target         import Enum__Edge_Bench__Target
from sg_compute_specs.sg_edge.bench.schemas.List__Edge_Bench__Metric       import List__Edge_Bench__Metric


class Schema__Edge_Bench__Scenario_Result(Type_Safe):
    id      : str
    name    : str
    tier    : Enum__Edge_Bench__Tier   = Enum__Edge_Bench__Tier.PRIMITIVE
    target  : Enum__Edge_Bench__Target = Enum__Edge_Bench__Target.LOCAL
    runs    : int = 0
    metrics : List__Edge_Bench__Metric
    passed  : bool = True
    skipped : bool = False                                                           # True when the scenario can't run on the chosen target
    note    : str                                                                    # skip reason or error message
