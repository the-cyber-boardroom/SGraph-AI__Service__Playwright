# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: List__Schema__Elastic__Health__Check
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe__List                                          import Type_Safe__List

from sg_compute_specs.elastic.schemas.Schema__Elastic__Health__Check                import Schema__Elastic__Health__Check


class List__Schema__Elastic__Health__Check(Type_Safe__List):
    expected_type = Schema__Elastic__Health__Check
