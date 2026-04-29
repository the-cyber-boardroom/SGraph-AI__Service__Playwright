# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Linux
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.linux.fast_api.routes.Routes__Linux__Stack   import Routes__Linux__Stack
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                 import Linux__Service


class Plugin__Manifest__Linux(Plugin__Manifest__Base):
    name         : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('linux')
    display_name : str                     = 'Bare Linux'
    description  : str                     = 'Plain EC2 instance, SSM access only.'
    enabled      : bool                    = True
    stability    : Enum__Plugin__Stability = Enum__Plugin__Stability.STABLE

    def service_class(self):
        return Linux__Service

    def routes_classes(self):
        return [Routes__Linux__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.LINUX,
            display_name          = self.display_name,
            description           = self.description,
            available             = True,
            default_instance_type = 't3.medium',
            expected_boot_seconds = 60,
            create_endpoint_path  = '/linux/stack',
            list_endpoint_path    = '/linux/stacks',
            info_endpoint_path    = '/linux/stack/{name}',
            delete_endpoint_path  = '/linux/stack/{name}',
            health_endpoint_path  = '/linux/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['linux:stack.created', 'linux:stack.deleted']
