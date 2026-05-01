# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__AMI__Create__Response
# Returned when an AMI bake is submitted. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Stack__Name import Safe_Str__Firefox__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Schema__Firefox__AMI__Create__Response(Type_Safe):
    ami_id      : Safe_Str__AMI__Id
    ami_name    : Safe_Str__Text
    stack_name  : Safe_Str__Firefox__Stack__Name
    instance_id : Safe_Str__Instance__Id
    region      : Safe_Str__AWS__Region
    state       : Safe_Str__Text                                                    # pending on submit
    elapsed_ms  : int = 0
