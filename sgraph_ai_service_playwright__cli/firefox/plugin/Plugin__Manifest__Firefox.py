# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Firefox
# Firefox is a lightweight remote browser experiment (jlesage/firefox, noVNC
# web UI on port 5800). Enabled=True for the structured experiment alongside
# Neko — results determine which remote-browser approach ships by default.
#
# To disable without redeploying: set PLUGIN__FIREFOX__ENABLED=false env var.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability   import Enum__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group    import Enum__Plugin__Nav_Group
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.firefox.fast_api.routes.Routes__Firefox__Stack import Routes__Firefox__Stack
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Service             import Firefox__Service


class Plugin__Manifest__Firefox(Plugin__Manifest__Base):
    name                 : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('firefox')
    display_name         : str                     = 'Firefox (noVNC browser, experimental)'
    description          : str                     = 'jlesage/firefox self-hosted browser via noVNC web UI on port 5800.'
    icon                 : str                     = '🦊'
    enabled              : bool                    = True
    stability            : Enum__Plugin__Stability = Enum__Plugin__Stability.EXPERIMENTAL
    boot_seconds_typical : int                     = 90
    nav_group            : Enum__Plugin__Nav_Group = Enum__Plugin__Nav_Group.COMPUTE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capabilities.append(Enum__Plugin__Capability.VAULT_WRITES)
        self.capabilities.append(Enum__Plugin__Capability.MITM_PROXY)
        self.capabilities.append(Enum__Plugin__Capability.IFRAME_EMBED)
        self.capabilities.append(Enum__Plugin__Capability.AMI_BAKE)

    def service_class(self):
        return Firefox__Service

    def routes_classes(self):
        return [Routes__Firefox__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.FIREFOX,
            display_name          = self.display_name,
            description           = self.description,
            available             = True,
            default_instance_type = 't3.medium',
            expected_boot_seconds = 90,
            create_endpoint_path  = '/firefox/stack',
            list_endpoint_path    = '/firefox/stacks',
            info_endpoint_path    = '/firefox/stack/{name}',
            delete_endpoint_path  = '/firefox/stack/{name}',
            health_endpoint_path  = '/firefox/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['firefox:stack.created', 'firefox:stack.deleted']
