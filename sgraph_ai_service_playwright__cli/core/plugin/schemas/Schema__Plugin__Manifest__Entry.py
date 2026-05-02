# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Plugin__Manifest__Entry
# Typed description of one plugin as returned by GET /catalog/manifest.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text            import Safe_Str__Text

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type                  import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.primitives.Safe_Str__Endpoint__Path      import Safe_Str__Endpoint__Path
from sgraph_ai_service_playwright__cli.core.plugin.collections.List__Plugin__Capability import List__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Capability       import Enum__Plugin__Capability
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Nav_Group        import Enum__Plugin__Nav_Group
from sgraph_ai_service_playwright__cli.core.plugin.enums.Enum__Plugin__Stability        import Enum__Plugin__Stability
from sgraph_ai_service_playwright__cli.core.plugin.primitives.Safe_Str__Icon            import Safe_Str__Icon


class Schema__Plugin__Manifest__Entry(Type_Safe):
    type_id              : Enum__Stack__Type
    display_name         : Safe_Str__Text
    description          : Safe_Str__Text
    icon                 : Safe_Str__Icon                           # emoji or short string for the UI card
    stability            : Enum__Plugin__Stability
    boot_seconds_typical : int                        = 60
    create_endpoint_path : Safe_Str__Endpoint__Path                 # e.g. /firefox/stack
    capabilities         : List__Plugin__Capability
    soon                 : bool                  = False            # True → UI shows "coming soon" badge
    nav_group            : Enum__Plugin__Nav_Group = Enum__Plugin__Nav_Group.COMPUTE
