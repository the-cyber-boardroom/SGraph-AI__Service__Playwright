# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__OpenSearch
# enabled=False: experimental until fully hardened. Routes and catalog entry
# exist but are excluded from startup and catalog by default.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.opensearch.fast_api.routes.Routes__OpenSearch__Stack \
                                                                                    import Routes__OpenSearch__Stack
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Service       import OpenSearch__Service


class Plugin__Manifest__OpenSearch(Plugin__Manifest__Base):
    name         : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('opensearch')
    display_name : str                     = 'OpenSearch + Dashboards'
    description  : str                     = 'Coming soon.'
    enabled      : bool                    = False
    stability    : Enum__Plugin__Stability = Enum__Plugin__Stability.EXPERIMENTAL

    def service_class(self):
        return OpenSearch__Service

    def routes_classes(self):
        return [Routes__OpenSearch__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.OPENSEARCH,
            display_name          = self.display_name,
            description           = self.description,
            available             = False,
            default_instance_type = 't3.medium',
            expected_boot_seconds = 120,
            create_endpoint_path  = '/opensearch/stack',
            list_endpoint_path    = '/opensearch/stacks',
            info_endpoint_path    = '/opensearch/stack/{name}',
            delete_endpoint_path  = '/opensearch/stack/{name}',
            health_endpoint_path  = '/opensearch/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['opensearch:stack.created', 'opensearch:stack.deleted']
