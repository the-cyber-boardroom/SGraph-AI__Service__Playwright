# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Schema__Firefox__Stack__Create__Request
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sg_compute_specs.firefox.primitives.Safe_Str__Firefox__Stack__Name             import Safe_Str__Firefox__Stack__Name
from sg_compute_specs.firefox.primitives.Safe_Str__Firefox__Interceptor__Source     import Safe_Str__Firefox__Interceptor__Source
from sg_compute_specs.firefox.primitives.Safe_Str__IP__Address                      import Safe_Str__IP__Address
from sg_compute_specs.firefox.schemas.Schema__Firefox__Interceptor__Choice          import Schema__Firefox__Interceptor__Choice


class Schema__Firefox__Stack__Create__Request(Type_Safe):
    stack_name    : Safe_Str__Firefox__Stack__Name
    region        : Safe_Str__Text
    caller_ip     : Safe_Str__IP__Address
    from_ami      : Safe_Str__Text
    instance_type : Safe_Str__Text
    password      : Safe_Str__Text
    interceptor   : Schema__Firefox__Interceptor__Choice
    env_source    : Safe_Str__Firefox__Interceptor__Source
    allowed_cidr  : Safe_Str__Text
    max_hours     : int = 1
