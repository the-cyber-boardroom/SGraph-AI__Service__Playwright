# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Vnc
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability   import Enum__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group    import Enum__Plugin__Nav_Group
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Flows       import Routes__Vnc__Flows
from sgraph_ai_service_playwright__cli.vnc.fast_api.routes.Routes__Vnc__Stack       import Routes__Vnc__Stack
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                     import Vnc__Service


class Plugin__Manifest__Vnc(Plugin__Manifest__Base):
    name                 : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('vnc')
    display_name         : str                     = 'VNC bastion (browser-in-browser)'
    description          : str                     = 'Full desktop browser-in-browser with mitmweb traffic inspection.'
    icon                 : str                     = '🖥️'
    enabled              : bool                    = True
    stability            : Enum__Plugin__Stability = Enum__Plugin__Stability.STABLE
    boot_seconds_typical : int                     = 120
    nav_group            : Enum__Plugin__Nav_Group = Enum__Plugin__Nav_Group.COMPUTE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capabilities.append(Enum__Plugin__Capability.MITM_PROXY)
        self.capabilities.append(Enum__Plugin__Capability.IFRAME_EMBED)

    def service_class(self):
        return Vnc__Service

    def routes_classes(self):
        return [Routes__Vnc__Stack, Routes__Vnc__Flows]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.VNC,
            display_name          = self.display_name,
            description           = self.description,
            available             = True,
            default_instance_type = 't3.large',
            expected_boot_seconds = 120,
            create_endpoint_path  = '/vnc/stack',
            list_endpoint_path    = '/vnc/stacks',
            info_endpoint_path    = '/vnc/stack/{name}',
            delete_endpoint_path  = '/vnc/stack/{name}',
            health_endpoint_path  = '/vnc/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['vnc:stack.created', 'vnc:stack.deleted', 'vnc:stack.health.changed']
