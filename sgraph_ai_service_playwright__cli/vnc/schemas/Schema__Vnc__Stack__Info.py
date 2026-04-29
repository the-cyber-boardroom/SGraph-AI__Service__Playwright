# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vnc__Stack__Info
# Public view of one ephemeral browser-viewer stack. Does NOT include
# operator_password — that is only returned once on create. Callers who lost
# the password must delete and recreate the stack.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__IP__Address         import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Stack__Name    import Safe_Str__Vnc__Stack__Name


class Schema__Vnc__Stack__Info(Type_Safe):
    stack_name        : Safe_Str__Vnc__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Id
    allowed_ip        : Safe_Str__IP__Address                                       # /32 recorded at create time (sg:allowed-ip tag)
    public_ip         : Safe_Str__Text                                              # Dots preserved
    viewer_url        : Safe_Str__Url                                               # https://<ip>/
    mitmweb_url       : Safe_Str__Url                                               # https://<ip>/mitmweb/
    interceptor_kind  : Enum__Vnc__Interceptor__Kind = Enum__Vnc__Interceptor__Kind.NONE
    interceptor_name  : Safe_Str__Id                                                # 'header_logger' / 'inline' / '' (none) — read from sg:interceptor tag
    state             : Enum__Vnc__Stack__State     = Enum__Vnc__Stack__State.UNKNOWN
    launch_time       : Safe_Str__Text                                              # ISO-8601 EC2 LaunchTime
    uptime_seconds    : int                          = 0
