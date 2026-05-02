# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Schema__Prom__Stack__List
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region

from sg_compute_specs.prometheus.collections.List__Schema__Prom__Stack__Info        import List__Schema__Prom__Stack__Info


class Schema__Prom__Stack__List(Type_Safe):
    region : Safe_Str__AWS__Region
    stacks : List__Schema__Prom__Stack__Info
