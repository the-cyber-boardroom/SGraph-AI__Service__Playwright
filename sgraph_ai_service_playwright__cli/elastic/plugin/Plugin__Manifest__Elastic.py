# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Elastic
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.elastic.fast_api.routes.Routes__Elastic__Stack import Routes__Elastic__Stack
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__Service              import Elastic__Service


class Plugin__Manifest__Elastic(Plugin__Manifest__Base):
    name         : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('elastic')
    display_name : str                     = 'Elastic + Kibana'
    description  : str                     = 'Single-node Elasticsearch + Kibana on EC2.'
    enabled      : bool                    = True
    stability    : Enum__Plugin__Stability = Enum__Plugin__Stability.STABLE

    def service_class(self):
        return Elastic__Service

    def routes_classes(self):
        return [Routes__Elastic__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.ELASTIC,
            display_name          = self.display_name,
            description           = self.description,
            available             = True,
            default_instance_type = 't3.medium',
            expected_boot_seconds = 90,
            create_endpoint_path  = '/elastic/stack',
            list_endpoint_path    = '/elastic/stacks',
            info_endpoint_path    = '/elastic/stack/{name}',
            delete_endpoint_path  = '/elastic/stack/{name}',
            health_endpoint_path  = '/elastic/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['elastic:stack.created', 'elastic:stack.deleted']
