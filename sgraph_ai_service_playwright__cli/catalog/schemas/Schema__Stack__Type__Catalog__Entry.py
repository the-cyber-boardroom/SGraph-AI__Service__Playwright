# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Type__Catalog__Entry
# Metadata for one stack type. Endpoint paths are data so the UI never
# hard-codes them.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type


class Schema__Stack__Type__Catalog__Entry(Type_Safe):
    type_id               : Enum__Stack__Type
    display_name          : Safe_Str__Text
    description           : Safe_Str__Text
    available             : bool             = False
    default_instance_type : Safe_Str__Text
    default_max_hours     : int              = 4
    expected_boot_seconds : int              = 60
    create_endpoint_path  : Safe_Str__Text
    list_endpoint_path    : Safe_Str__Text
    info_endpoint_path    : Safe_Str__Text
    delete_endpoint_path  : Safe_Str__Text
    health_endpoint_path  : Safe_Str__Text
