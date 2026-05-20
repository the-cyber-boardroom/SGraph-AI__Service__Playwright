# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: List__Local__Edge__Issue
# Typed list of Schema__Local__Edge__Issue. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Issue import Schema__Local__Edge__Issue


class List__Local__Edge__Issue(Type_Safe__List):
    expected_type = Schema__Local__Edge__Issue
