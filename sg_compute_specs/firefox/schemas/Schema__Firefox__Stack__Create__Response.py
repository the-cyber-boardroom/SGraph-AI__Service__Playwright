# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Schema__Firefox__Stack__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sg_compute_specs.firefox.enums.Enum__Firefox__Stack__State                     import Enum__Firefox__Stack__State
from sg_compute_specs.firefox.primitives.Safe_Str__Firefox__Stack__Name             import Safe_Str__Firefox__Stack__Name


class Schema__Firefox__Stack__Create__Response(Type_Safe):
    stack_name        : Safe_Str__Firefox__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Text
    region            : Safe_Str__Text
    ami_id            : Safe_Str__Text
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Text
    caller_ip         : Safe_Str__Text
    password          : Safe_Str__Text
    interceptor_label : Safe_Str__Text
    mitmweb_url       : Safe_Str__Url
    state             : Enum__Firefox__Stack__State = Enum__Firefox__Stack__State.PENDING
    elapsed_ms        : int = 0
