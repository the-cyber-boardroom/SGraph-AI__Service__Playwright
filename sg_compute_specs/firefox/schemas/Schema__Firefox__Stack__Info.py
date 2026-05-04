# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Schema__Firefox__Stack__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sg_compute_specs.firefox.enums.Enum__Firefox__Stack__State                     import Enum__Firefox__Stack__State
from sg_compute_specs.firefox.primitives.Safe_Str__Firefox__Stack__Name             import Safe_Str__Firefox__Stack__Name
from sg_compute_specs.firefox.primitives.Safe_Str__IP__Address                      import Safe_Str__IP__Address


class Schema__Firefox__Stack__Info(Type_Safe):
    stack_name        : Safe_Str__Firefox__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Text
    region            : Safe_Str__Text
    ami_id            : Safe_Str__Text
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Text
    allowed_ip        : Safe_Str__IP__Address
    public_ip         : Safe_Str__IP__Address
    viewer_url        : Safe_Str__Url
    mitmweb_url       : Safe_Str__Url
    state             : Enum__Firefox__Stack__State = Enum__Firefox__Stack__State.UNKNOWN
    launch_time       : Safe_Str__Text
    uptime_seconds    : int = 0
