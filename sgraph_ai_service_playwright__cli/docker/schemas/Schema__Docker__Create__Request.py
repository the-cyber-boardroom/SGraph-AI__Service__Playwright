# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Docker__Create__Request
# Inputs for `sp docker create [NAME]`. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.docker.primitives.Safe_Str__IP__Address      import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.docker.primitives.Safe_Str__Docker__Stack__Name import Safe_Str__Docker__Stack__Name


DEFAULT_API_KEY_NAME = 'X-API-Key'


class Schema__Docker__Create__Request(Type_Safe):
    stack_name    : Safe_Str__Docker__Stack__Name
    region        : Safe_Str__AWS__Region
    instance_type : Safe_Str__Text           = 't3.medium'
    from_ami      : Safe_Str__AMI__Id
    caller_ip     : Safe_Str__IP__Address
    api_key_name  : Safe_Str__Text           = DEFAULT_API_KEY_NAME                # Header name for host control plane auth
    api_key_value : Safe_Str__Text                                                  # Generated randomly if empty
    open_to_all   : bool                     = False                               # Open SG to 0.0.0.0/0 instead of caller /32
    use_spot      : bool                     = True                                 # Spot instance by default; pass use_spot=False for on-demand
    max_hours     : int                      = 1                                    # Auto-terminate after N hours; 0 = no timer
    extra_ports   : List[int]                                                       # TCP ports to open from caller /32
