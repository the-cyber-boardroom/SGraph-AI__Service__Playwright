# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: List__Local__Edge__Usecase_Step
# Typed list of Schema__Local__Edge__Usecase_Step. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List          import Type_Safe__List

from sg_compute_specs.sg_edge.local.usecases.Schema__Local__Edge__Usecase_Step  import Schema__Local__Edge__Usecase_Step


class List__Local__Edge__Usecase_Step(Type_Safe__List):
    expected_type = Schema__Local__Edge__Usecase_Step
