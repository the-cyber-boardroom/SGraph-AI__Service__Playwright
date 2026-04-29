# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Docker
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.docker.fast_api.routes.Routes__Docker__Stack  import Routes__Docker__Stack
from sgraph_ai_service_playwright__cli.docker.service.Docker__Service                import Docker__Service


class Plugin__Manifest__Docker(Plugin__Manifest__Base):
    name         : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('docker')
    display_name : str                     = 'Docker host'
    description  : str                     = 'EC2 with Docker + Compose pre-installed.'
    enabled      : bool                    = True
    stability    : Enum__Plugin__Stability = Enum__Plugin__Stability.STABLE

    def service_class(self):
        return Docker__Service

    def routes_classes(self):
        return [Routes__Docker__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.DOCKER,
            display_name          = self.display_name,
            description           = self.description,
            available             = True,
            default_instance_type = 't3.medium',
            expected_boot_seconds = 600,
            create_endpoint_path  = '/docker/stack',
            list_endpoint_path    = '/docker/stacks',
            info_endpoint_path    = '/docker/stack/{name}',
            delete_endpoint_path  = '/docker/stack/{name}',
            health_endpoint_path  = '/docker/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['docker:stack.created', 'docker:stack.deleted']
