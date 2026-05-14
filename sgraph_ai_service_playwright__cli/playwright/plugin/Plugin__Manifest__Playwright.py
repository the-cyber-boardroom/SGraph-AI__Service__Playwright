# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Playwright
# Manifest for the `sp playwright` section: ephemeral Playwright FastAPI
# instances launched as pods on a host via the host-plane pods API.
# Mirrors Plugin__Manifest__Vnc.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability   import Enum__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group    import Enum__Plugin__Nav_Group
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.playwright.fast_api.routes.Routes__Playwright__Stack import Routes__Playwright__Stack
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Service import Playwright__Stack__Service


class Plugin__Manifest__Playwright(Plugin__Manifest__Base):
    name                 : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('playwright')
    display_name         : str                     = 'Playwright (browser automation API)'
    description          : str                     = ('Ephemeral Playwright FastAPI instances — declarative step '
                                                       'sequences, screenshots, navigation. One diniscruz/sg-playwright '
                                                       'pod per stack, launched on a host via the host-plane pods API.')
    icon                 : str                     = '🎭'
    enabled              : bool                    = True
    stability            : Enum__Plugin__Stability = Enum__Plugin__Stability.EXPERIMENTAL
    boot_seconds_typical : int                     = 15
    nav_group            : Enum__Plugin__Nav_Group = Enum__Plugin__Nav_Group.COMPUTE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capabilities.append(Enum__Plugin__Capability.MITM_PROXY)               # --with-mitmproxy (design doc §9; not yet wired)
        self.capabilities.append(Enum__Plugin__Capability.VAULT_WRITES)             # the running app stages artefacts via the VAULT sink

    def service_class(self):
        return Playwright__Stack__Service

    def routes_classes(self):
        return [Routes__Playwright__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.PLAYWRIGHT,
            display_name          = self.display_name           ,
            description           = self.description            ,
            available             = True                        ,
            default_instance_type = 't3.medium'                 ,
            expected_boot_seconds = 15                           ,
            create_endpoint_path  = '/playwright/stack'          ,
            list_endpoint_path    = '/playwright/stacks'         ,
            info_endpoint_path    = '/playwright/stack/{name}'   ,
            delete_endpoint_path  = '/playwright/stack/{name}'   ,
            health_endpoint_path  = '/playwright/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['playwright:stack.created', 'playwright:stack.deleted']
