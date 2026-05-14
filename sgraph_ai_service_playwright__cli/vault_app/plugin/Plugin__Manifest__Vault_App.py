# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Vault_App
# Manifest entry for the vault-app compute plugin. Registers the service,
# routes, and catalog entry consumed by Fast_API__SP__CLI and the UI.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry \
                                                                                    import Schema__Stack__Type__Catalog__Entry
from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Manifest__Base           import Plugin__Manifest__Base
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability   import Enum__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group    import Enum__Plugin__Nav_Group
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability    import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name import Safe_Str__Plugin__Name
from sgraph_ai_service_playwright__cli.vault_app.fast_api.routes.Routes__Vault_App__Stack \
                                                                                    import Routes__Vault_App__Stack
from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__Service         import Vault_App__Service


class Plugin__Manifest__Vault_App(Plugin__Manifest__Base):
    name                 : Safe_Str__Plugin__Name  = Safe_Str__Plugin__Name('vault_app')
    display_name         : str                     = 'Vault App'
    description          : str                     = 'Self-contained vault + browser automation + passive MITM stack on EC2.'
    icon                 : str                     = '🗄️'
    enabled              : bool                    = True
    stability            : Enum__Plugin__Stability = Enum__Plugin__Stability.EXPERIMENTAL
    boot_seconds_typical : int                     = 90
    nav_group            : Enum__Plugin__Nav_Group = Enum__Plugin__Nav_Group.COMPUTE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capabilities.append(Enum__Plugin__Capability.VAULT_WRITES  )
        self.capabilities.append(Enum__Plugin__Capability.MITM_PROXY    )
        self.capabilities.append(Enum__Plugin__Capability.REMOTE_SHELL  )
        self.capabilities.append(Enum__Plugin__Capability.SIDECAR_ATTACH)

    def service_class(self):
        return Vault_App__Service

    def routes_classes(self):
        return [Routes__Vault_App__Stack]

    def catalog_entry(self):
        return Schema__Stack__Type__Catalog__Entry(
            type_id               = Enum__Stack__Type.VAULT_APP                ,
            display_name          = self.display_name                          ,
            description           = self.description                           ,
            available             = True                                       ,
            default_instance_type = 't3.medium'                                ,
            expected_boot_seconds = 90                                         ,
            create_endpoint_path  = '/vault-app/stack'                         ,
            list_endpoint_path    = '/vault-app/stacks'                        ,
            info_endpoint_path    = '/vault-app/stack/{name}'                  ,
            delete_endpoint_path  = '/vault-app/stack/{name}'                  ,
            health_endpoint_path  = '/vault-app/stack/{name}/health'           ,
        )

    def event_topics_emitted(self):
        return ['vault_app:stack.created', 'vault_app:stack.deleted']
