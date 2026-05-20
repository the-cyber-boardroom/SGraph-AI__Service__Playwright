# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: List__Local__Edge__Slug
# Typed list of Schema__Local__Edge__Slug. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Slug import Schema__Local__Edge__Slug


class List__Local__Edge__Slug(Type_Safe__List):
    expected_type = Schema__Local__Edge__Slug
