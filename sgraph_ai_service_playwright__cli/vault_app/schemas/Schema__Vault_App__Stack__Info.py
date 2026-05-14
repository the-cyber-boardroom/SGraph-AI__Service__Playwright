# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vault_App__Stack__Info
# Public view of one running vault-app EC2 stack. Does NOT include the
# access token — that is only returned once on create. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.vault_app.enums.Enum__Vault_App__Stack__State import Enum__Vault_App__Stack__State
from sgraph_ai_service_playwright__cli.vault_app.primitives.Safe_Str__Vault_App__Stack__Name import Safe_Str__Vault_App__Stack__Name


class Schema__Vault_App__Stack__Info(Type_Safe):
    stack_name        : Safe_Str__Vault_App__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Id
    public_ip         : Safe_Str__Text
    vault_url         : Safe_Str__Url                                               # http(s)://<ip>:8080/
    state             : Enum__Vault_App__Stack__State = Enum__Vault_App__Stack__State.UNKNOWN
    launch_time       : Safe_Str__Text
    uptime_seconds    : int = 0
