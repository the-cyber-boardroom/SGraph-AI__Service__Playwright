# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: List__Schema__OS__Stack__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe__List                                          import Type_Safe__List

from sg_compute_specs.opensearch.schemas.Schema__OS__Stack__Info                    import Schema__OS__Stack__Info


class List__Schema__OS__Stack__Info(Type_Safe__List):
    expected_type = Schema__OS__Stack__Info
