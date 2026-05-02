# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Schema__Vnc__Stack__Create__Response
# Carries the generated operator password — returned once only.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region

from sg_compute_specs.vnc.enums.Enum__Vnc__Interceptor__Kind                        import Enum__Vnc__Interceptor__Kind
from sg_compute_specs.vnc.enums.Enum__Vnc__Stack__State                             import Enum__Vnc__Stack__State
from sg_compute_specs.vnc.primitives.Safe_Str__IP__Address                          import Safe_Str__IP__Address
from sg_compute_specs.vnc.primitives.Safe_Str__Vnc__Password                        import Safe_Str__Vnc__Password
from sg_compute_specs.vnc.primitives.Safe_Str__Vnc__Stack__Name                     import Safe_Str__Vnc__Stack__Name


class Schema__Vnc__Stack__Create__Response(Type_Safe):
    stack_name           : Safe_Str__Vnc__Stack__Name
    aws_name_tag         : Safe_Str__Text
    instance_id          : Safe_Str__Instance__Id
    region               : Safe_Str__AWS__Region
    ami_id               : Safe_Str__AMI__Id
    instance_type        : Safe_Str__Text
    security_group_id    : Safe_Str__Id
    caller_ip            : Safe_Str__IP__Address
    public_ip            : Safe_Str__Text
    viewer_url           : Safe_Str__Url
    mitmweb_url          : Safe_Str__Url
    operator_username    : Safe_Str__Id                = 'operator'
    operator_password    : Safe_Str__Vnc__Password
    interceptor_kind     : Enum__Vnc__Interceptor__Kind = Enum__Vnc__Interceptor__Kind.NONE
    interceptor_name     : Safe_Str__Id
    state                : Enum__Vnc__Stack__State     = Enum__Vnc__Stack__State.PENDING
