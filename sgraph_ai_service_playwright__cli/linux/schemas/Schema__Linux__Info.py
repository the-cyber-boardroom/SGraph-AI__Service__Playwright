# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Linux__Info
# Public view of one ephemeral Linux EC2 stack. No password field —
# access is via SSM only (no SSH, no stored credentials). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.linux.enums.Enum__Linux__Stack__State        import Enum__Linux__Stack__State
from sgraph_ai_service_playwright__cli.linux.primitives.Safe_Str__IP__Address       import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.linux.primitives.Safe_Str__Linux__Stack__Name import Safe_Str__Linux__Stack__Name


class Schema__Linux__Info(Type_Safe):
    stack_name        : Safe_Str__Linux__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Text
    allowed_ip        : Safe_Str__IP__Address
    public_ip         : Safe_Str__Text
    state             : Enum__Linux__Stack__State = Enum__Linux__Stack__State.UNKNOWN
    launch_time       : Safe_Str__Text
    uptime_seconds    : int = 0
