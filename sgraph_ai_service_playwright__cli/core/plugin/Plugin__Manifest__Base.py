# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Plugin__Manifest__Base
# Pure data + factory methods for one compute-type plugin. Subclasses live in
# {plugin}/plugin/Plugin__Manifest__{Name}.py — one per plugin folder.
#
# Rules:
#   - Pure data + factory methods only. No business logic.
#   - service_class / routes_classes / catalog_entry must be overridden.
#   - event_topics_* are declarative lists (actual emit calls are in services).
#   - setup() is the one lifecycle hook called once by Plugin__Registry.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text            import Safe_Str__Text

from sgraph_ai_service_playwright__cli.core.plugin.collections.List__Plugin__Capability import List__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group        import Enum__Plugin__Nav_Group
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability        import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Icon            import Safe_Str__Icon
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name    import Safe_Str__Plugin__Name


class Plugin__Manifest__Base(Type_Safe):
    name                 : Safe_Str__Plugin__Name                               # matches folder name, e.g. 'podman', 'vnc'
    display_name         : Safe_Str__Text
    description          : Safe_Str__Text
    icon                 : Safe_Str__Icon          = ''                         # emoji for the UI card
    enabled              : bool                    = False                      # default off — subclasses opt in explicitly
    stability            : Enum__Plugin__Stability = Enum__Plugin__Stability.EXPERIMENTAL
    requires_aws         : bool                    = True
    boot_seconds_typical : int                     = 60
    soon                 : bool                    = False                      # True → UI shows "coming soon" badge
    nav_group            : Enum__Plugin__Nav_Group = Enum__Plugin__Nav_Group.COMPUTE
    capabilities         : List__Plugin__Capability

    # ── factory methods (must override) ─────────────────────────────────────

    def service_class(self) -> type:
        raise NotImplementedError(f'{self.name}: service_class()')

    def routes_classes(self) -> list:
        raise NotImplementedError(f'{self.name}: routes_classes()')

    def catalog_entry(self):
        raise NotImplementedError(f'{self.name}: catalog_entry()')

    def manifest_entry(self):
        from sgraph_ai_service_playwright__cli.core.plugin.schemas.Schema__Plugin__Manifest__Entry import Schema__Plugin__Manifest__Entry
        entry = self.catalog_entry()
        caps  = List__Plugin__Capability()
        for c in self.capabilities:
            caps.append(c)
        return Schema__Plugin__Manifest__Entry(
            type_id              = entry.type_id              ,
            display_name         = self.display_name          ,
            description          = self.description           ,
            icon                 = self.icon                  ,
            stability            = self.stability             ,
            boot_seconds_typical = self.boot_seconds_typical  ,
            create_endpoint_path = entry.create_endpoint_path ,
            capabilities         = caps                       ,
            soon                 = self.soon                  ,
            nav_group            = self.nav_group             ,
        )

    # ── declarative lists (optional override) ───────────────────────────────

    def event_topics_emitted(self) -> list:                                     # documents which events this plugin fires
        return []

    def event_topics_listened(self) -> list:                                    # documents which events this plugin reacts to
        return []

    # ── lifecycle (optional override) ───────────────────────────────────────

    def setup(self) -> None:                                                    # called once by Plugin__Registry.setup_all(); use for lazy AWS client init
        pass
