# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: List__Edge_Bench__Metric
# Typed list of Schema__Edge_Bench__Metric. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List       import Type_Safe__List

from sg_compute_specs.sg_edge.bench.schemas.Schema__Edge_Bench__Metric       import Schema__Edge_Bench__Metric


class List__Edge_Bench__Metric(Type_Safe__List):
    expected_type = Schema__Edge_Bench__Metric
