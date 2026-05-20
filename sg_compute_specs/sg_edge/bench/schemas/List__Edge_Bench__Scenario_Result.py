# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: List__Edge_Bench__Scenario_Result
# Typed list of Schema__Edge_Bench__Scenario_Result. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List              import Type_Safe__List

from sg_compute_specs.sg_edge.bench.schemas.Schema__Edge_Bench__Scenario_Result    import Schema__Edge_Bench__Scenario_Result


class List__Edge_Bench__Scenario_Result(Type_Safe__List):
    expected_type = Schema__Edge_Bench__Scenario_Result
