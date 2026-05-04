# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vnc__Stack__Create__Request
# Inputs for `sp vnc create [NAME]`. All fields optional — service generates
# a random name, detects caller IP, generates the operator password, picks
# the latest AL2023 AMI when none of those are supplied.
#
# `interceptor` carries the N5 selector — defaults to kind=NONE so mitmproxy
# starts with no interceptor unless explicitly chosen.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__IP__Address         import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Password       import Safe_Str__Vnc__Password
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Stack__Name    import Safe_Str__Vnc__Stack__Name
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Interceptor__Choice import Schema__Vnc__Interceptor__Choice


class Schema__Vnc__Stack__Create__Request(Type_Safe):
    stack_name        : Safe_Str__Vnc__Stack__Name = ''                             # Empty → service generates "vnc-{adj}-{scientist}"
    region            : Safe_Str__AWS__Region      = ''                             # Empty → resolved from AWS_Config
    instance_type     : Safe_Str__Text             = ''                             # Safe_Str__Text preserves the dot in 't3.medium'
    from_ami          : Safe_Str__AMI__Id          = ''                             # Empty → latest AL2023 resolved by service
    caller_ip         : Safe_Str__IP__Address      = ''                             # Empty → service calls Caller__IP__Detector
    max_hours         : int                        = 1                              # Auto-terminate after N hours; 0 disables
    operator_password : Safe_Str__Vnc__Password    = ''                             # Empty → service generates one (used for nginx Basic auth + MITM_PROXYAUTH)
    public_ingress    : bool                       = False                          # When True, SG ingress on 443 opens to 0.0.0.0/0 instead of caller_ip/32. Reasonable for the debug viewer since it's behind nginx Basic auth + bcrypt.
    use_spot          : bool                       = True                           # Spot instance by default; pass use_spot=False for on-demand
    interceptor       : Schema__Vnc__Interceptor__Choice                            # Defaults to kind=NONE per N5
