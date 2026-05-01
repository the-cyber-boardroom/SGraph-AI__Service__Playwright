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

from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability        import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Plugin__Name    import Safe_Str__Plugin__Name


class Plugin__Manifest__Base(Type_Safe):
    name         : Safe_Str__Plugin__Name                                       # matches folder name, e.g. 'linux', 'vnc'
    display_name : Safe_Str__Text
    description  : Safe_Str__Text
    enabled      : bool                      = False                            # default off — subclasses opt in explicitly
    stability    : Enum__Plugin__Stability   = Enum__Plugin__Stability.EXPERIMENTAL
    requires_aws : bool                      = True

    # ── factory methods (must override) ─────────────────────────────────────

    def service_class(self) -> type:
        raise NotImplementedError(f'{self.name}: service_class()')

    def routes_classes(self) -> list:
        raise NotImplementedError(f'{self.name}: routes_classes()')

    def catalog_entry(self):
        raise NotImplementedError(f'{self.name}: catalog_entry()')

    # ── declarative lists (optional override) ───────────────────────────────

    def event_topics_emitted(self) -> list:                                     # documents which events this plugin fires
        return []

    def event_topics_listened(self) -> list:                                    # documents which events this plugin reacts to
        return []

    # ── lifecycle (optional override) ───────────────────────────────────────

    def setup(self) -> None:                                                    # called once by Plugin__Registry.setup_all(); use for lazy AWS client init
        pass
