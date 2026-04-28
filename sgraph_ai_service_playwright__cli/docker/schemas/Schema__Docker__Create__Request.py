# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Docker__Create__Request
# Inputs for `sp docker create [NAME]`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.docker.primitives.Safe_Str__IP__Address      import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.docker.primitives.Safe_Str__Docker__Stack__Name import Safe_Str__Docker__Stack__Name


class Schema__Docker__Create__Request(Type_Safe):
    stack_name    : Safe_Str__Docker__Stack__Name
    region        : Safe_Str__AWS__Region
    instance_type : Safe_Str__Text           = 't3.medium'
    from_ami      : Safe_Str__AMI__Id
    caller_ip     : Safe_Str__IP__Address
    max_hours     : int                      = 4
    extra_ports   : list                     = []
