# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Stack__Info
# Public view of one ephemeral Playwright stack (an EC2 instance). Does NOT
# carry the api_key — that is only echoed once on create.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text    import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id import Safe_Str__Id
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url        import Safe_Str__Url

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id         import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id    import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__IP__Address    import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name


class Schema__Playwright__Stack__Info(Type_Safe):
    stack_name        : Safe_Str__Playwright__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Id
    allowed_ip        : Safe_Str__IP__Address                                    # /32 recorded at create time (sg:allowed-ip tag)
    public_ip         : Safe_Str__Text                                           # Dots preserved
    playwright_url    : Safe_Str__Url                                            # http://<ip>:8000
    with_mitmproxy    : bool                          = False                    # From the sg:with-mitmproxy tag
    state             : Enum__Playwright__Stack__State = Enum__Playwright__Stack__State.UNKNOWN
    launch_time       : Safe_Str__Text                                           # ISO-8601 EC2 LaunchTime
