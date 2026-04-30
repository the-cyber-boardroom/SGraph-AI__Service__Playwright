# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Stack__Create__Response
# Returned once on create — password shown only here. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Firefox__Stack__State    import Enum__Firefox__Stack__State
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Stack__Name import Safe_Str__Firefox__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Schema__Firefox__Stack__Create__Response(Type_Safe):
    stack_name        : Safe_Str__Firefox__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Text
    caller_ip         : Safe_Str__Text
    password          : Safe_Str__Text                                              # web UI password — returned once, stash it
    proxy_host        : Safe_Str__Text
    proxy_port        : int = 0
    state             : Enum__Firefox__Stack__State = Enum__Firefox__Stack__State.PENDING
    elapsed_ms        : int = 0
