# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Schema__Vnc__Stack__Info
# Public view of one ephemeral VNC stack. No operator_password — returned
# once on create only. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sg_compute.platforms.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sg_compute.platforms.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sg_compute.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region

from sg_compute_specs.vnc.enums.Enum__Vnc__Interceptor__Kind                        import Enum__Vnc__Interceptor__Kind
from sg_compute_specs.vnc.enums.Enum__Vnc__Stack__State                             import Enum__Vnc__Stack__State
from sg_compute_specs.vnc.primitives.Safe_Str__IP__Address                          import Safe_Str__IP__Address
from sg_compute_specs.vnc.primitives.Safe_Str__Vnc__Stack__Name                     import Safe_Str__Vnc__Stack__Name


class Schema__Vnc__Stack__Info(Type_Safe):
    stack_name        : Safe_Str__Vnc__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Id
    allowed_ip        : Safe_Str__IP__Address
    public_ip         : Safe_Str__Text
    viewer_url        : Safe_Str__Url
    mitmweb_url       : Safe_Str__Url
    interceptor_kind  : Enum__Vnc__Interceptor__Kind = Enum__Vnc__Interceptor__Kind.NONE
    interceptor_name  : Safe_Str__Id
    state             : Enum__Vnc__Stack__State     = Enum__Vnc__Stack__State.UNKNOWN
    launch_time       : Safe_Str__Text
    uptime_seconds    : int                          = 0
