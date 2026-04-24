# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__Info
# Public view of one ephemeral stack. Does NOT include elastic_password — that
# is only returned once, on create. Callers who lost the password must delete
# and recreate the stack.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__State           import Enum__Elastic__State
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region


class Schema__Elastic__Info(Type_Safe):
    stack_name       : Safe_Str__Elastic__Stack__Name
    aws_name_tag     : Safe_Str__Text
    instance_id      : Safe_Str__Instance__Id
    region           : Safe_Str__AWS__Region
    ami_id           : Safe_Str__AMI__Id
    instance_type    : Safe_Str__Text                                               # Preserves the dot in "t3.medium"; see Schema__Elastic__Create__Request
    security_group_id: Safe_Str__Id
    allowed_ip       : Safe_Str__IP__Address                                        # The /32 recorded at create time (from the sg:allowed-ip tag)
    public_ip        : Safe_Str__Text                                               # Dots preserved; URL goes in kibana_url below
    kibana_url       : Safe_Str__Url                                                # Preserves "://" and ":port"
    state            : Enum__Elastic__State   = Enum__Elastic__State.UNKNOWN
