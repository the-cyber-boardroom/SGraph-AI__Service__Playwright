# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Podman
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.podman.fast_api.routes.Routes__Podman__Stack  import Routes__Podman__Stack
from sgraph_ai_service_playwright__cli.podman.service.Podman__Service                import Podman__Service


class Plugin__Manifest__Podman(Plugin__Manifest__Base):
    name         : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('podman')
    display_name : str                     = 'Podman host'
    description  : str                     = 'EC2 with Podman pre-installed (daemonless, rootless-capable).'
    enabled      : bool                    = True
    stability    : Enum__Plugin__Stability = Enum__Plugin__Stability.STABLE

    def service_class(self):
        return Podman__Service

    def routes_classes(self):
        return [Routes__Podman__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.PODMAN,
            display_name          = self.display_name,
            description           = self.description,
            available             = True,
            default_instance_type = 't3.medium',
            expected_boot_seconds = 120,
            create_endpoint_path  = '/podman/stack',
            list_endpoint_path    = '/podman/stacks',
            info_endpoint_path    = '/podman/stack/{name}',
            delete_endpoint_path  = '/podman/stack/{name}',
            health_endpoint_path  = '/podman/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['podman:stack.created', 'podman:stack.deleted']
