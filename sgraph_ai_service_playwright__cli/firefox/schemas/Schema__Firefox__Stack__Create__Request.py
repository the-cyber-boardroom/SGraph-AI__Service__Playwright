# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Stack__Create__Request
# Pure data. All fields optional — service fills in sensible defaults.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Stack__Name import Safe_Str__Firefox__Stack__Name
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region


class Schema__Firefox__Stack__Create__Request(Type_Safe):
    stack_name    : Safe_Str__Firefox__Stack__Name                                  # auto-generated when empty
    region        : Safe_Str__AWS__Region
    caller_ip     : Safe_Str__IP__Address                                           # auto-detected when empty
    from_ami      : Safe_Str__AMI__Id                                               # latest AL2023 when empty
    instance_type : Safe_Str__Text                                                  # defaults to t3.medium
    password      : Safe_Str__Text                                                  # web UI password; auto-generated when empty
