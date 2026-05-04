# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Prom__Stack__Info
# Ordered list of Prometheus stack infos returned by Prometheus__Service.list_stacks.
# Pure type definition; mirrors List__Schema__OS__Stack__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Info import Schema__Prom__Stack__Info


class List__Schema__Prom__Stack__Info(Type_Safe__List):
    expected_type = Schema__Prom__Stack__Info
