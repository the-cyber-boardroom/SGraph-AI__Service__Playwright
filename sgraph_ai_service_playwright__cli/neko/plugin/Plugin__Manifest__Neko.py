# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Neko
# Neko is a WebRTC-based self-hosted browser (n.eko). Plugin is enabled=True
# for the structured experiment (v0.22.19 brief, doc 04). Results determine
# whether Neko replaces VNC as the default remote browser.
#
# To disable without redeploying: set PLUGIN__NEKO__ENABLED=false env var.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability   import Enum__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group    import Enum__Plugin__Nav_Group
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.neko.fast_api.routes.Routes__Neko__Stack     import Routes__Neko__Stack
from sgraph_ai_service_playwright__cli.neko.service.Neko__Service                   import Neko__Service


class Plugin__Manifest__Neko(Plugin__Manifest__Base):
    name                 : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('neko')
    display_name         : str                     = 'Neko (WebRTC browser, experimental)'
    description          : str                     = 'n.eko self-hosted browser via WebRTC. Under evaluation — see neko/docs/README.md.'
    icon                 : str                     = '🦊'
    enabled              : bool                    = True                               # enabled for structured experiment — see neko/docs/README.md
    stability            : Enum__Plugin__Stability = Enum__Plugin__Stability.EXPERIMENTAL
    boot_seconds_typical : int                     = 120
    nav_group            : Enum__Plugin__Nav_Group = Enum__Plugin__Nav_Group.COMPUTE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capabilities.append(Enum__Plugin__Capability.IFRAME_EMBED)

    def service_class(self):
        return Neko__Service

    def routes_classes(self):
        return [Routes__Neko__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.NEKO,
            display_name          = self.display_name,
            description           = self.description,
            available             = True,                                       # experiment active — routes live
            default_instance_type = 't3.large',
            expected_boot_seconds = 120,
            create_endpoint_path  = '/neko/stack',
            list_endpoint_path    = '/neko/stacks',
            info_endpoint_path    = '/neko/stack/{name}',
            delete_endpoint_path  = '/neko/stack/{name}',
            health_endpoint_path  = '/neko/stack/{name}/health',
        )

    def event_topics_emitted(self):
        return ['neko:stack.created', 'neko:stack.deleted']
