# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: List__Schema__Prom__Stack__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sg_compute_specs.prometheus.schemas.Schema__Prom__Stack__Info                  import Schema__Prom__Stack__Info


class List__Schema__Prom__Stack__Info(Type_Safe__List):
    expected_type = Schema__Prom__Stack__Info
