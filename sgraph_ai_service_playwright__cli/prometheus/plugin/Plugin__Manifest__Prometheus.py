# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Prometheus
# enabled=False: experimental until fully hardened. Routes and catalog entry
# exist but are excluded from startup and catalog by default.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability   import Enum__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group    import Enum__Plugin__Nav_Group
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.prometheus.fast_api.routes.Routes__Prometheus__Stack \
                                                                                    import Routes__Prometheus__Stack
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Service       import Prometheus__Service


class Plugin__Manifest__Prometheus(Plugin__Manifest__Base):
    name                 : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('prometheus')
    display_name         : str                     = 'Prometheus + Grafana'
    description          : str                     = 'Single-node Prometheus + Grafana on EC2.'
    icon                 : str                     = '📊'
    enabled              : bool                    = False
    stability            : Enum__Plugin__Stability = Enum__Plugin__Stability.EXPERIMENTAL
    boot_seconds_typical : int                     = 90
    nav_group            : Enum__Plugin__Nav_Group = Enum__Plugin__Nav_Group.OBSERVABILITY

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capabilities.append(Enum__Plugin__Capability.METRICS)

    def service_class(self):
        return Prometheus__Service

    def routes_classes(self):
        return [Routes__Prometheus__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.PROMETHEUS,
            display_name          = self.display_name,
            description           = self.description,
            available             = False,
            default_instance_type = 't3.medium',
            expected_boot_seconds = 90,
            create_endpoint_path  = '/prometheus/stack',
            list_endpoint_path    = '/prometheus/stacks',
            info_endpoint_path    = '/prometheus/stack/{name}',
            delete_endpoint_path  = '/prometheus/stack/{name}',
            health_endpoint_path  = '/prometheus/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['prometheus:stack.created', 'prometheus:stack.deleted']
