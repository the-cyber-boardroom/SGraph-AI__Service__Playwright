# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Linux__Create__Request
# Inputs for `sp linux create [NAME]`. All fields optional — the service
# generates a name, detects caller IP, and picks defaults when empty.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.linux.primitives.Safe_Str__IP__Address       import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.linux.primitives.Safe_Str__Linux__Stack__Name import Safe_Str__Linux__Stack__Name


class Schema__Linux__Create__Request(Type_Safe):
    stack_name    : Safe_Str__Linux__Stack__Name                                    # Empty → service generates "{adj}-{sci}"
    region        : Safe_Str__AWS__Region                                           # Empty → resolved from AWS_Config session
    instance_type : Safe_Str__Text           = 't3.medium'                          # 2 vCPU / 4 GB
    from_ami      : Safe_Str__AMI__Id                                               # Empty → latest AL2023
    caller_ip     : Safe_Str__IP__Address                                           # Empty → service auto-detects from checkip.amazonaws.com
    max_hours     : int                      = 1                                    # Auto-terminate after N hours; 0 = no timer
    extra_ports   : List[int]                                                       # TCP ports to open from caller /32 (e.g. [8080, 3000])
