# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Stack__Create__Request
# Inputs for `sp playwright create [NAME]`. EC2 model: the stack is one fresh
# EC2 instance running a docker-compose stack of 2-3 containers via user-data.
# All fields optional — the service resolves defaults.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text    import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id         import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__IP__Address    import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Vault_Path     import Safe_Str__Vault_Path


class Schema__Playwright__Stack__Create__Request(Type_Safe):
    stack_name      : Safe_Str__Playwright__Stack__Name = ''                     # Empty → 'playwright-{adj}-{scientist}'
    region          : Safe_Str__AWS__Region             = ''                     # Empty → DEFAULT_REGION
    instance_type   : Safe_Str__Text                    = ''                     # Empty → DEFAULT_INSTANCE_TYPE ('t3.medium')
    from_ami        : Safe_Str__AMI__Id                 = ''                     # Empty → latest AL2023
    caller_ip       : Safe_Str__IP__Address             = ''                     # Empty → Caller__IP__Detector
    max_hours       : int                               = 1                      # 0 disables auto-terminate
    image_tag       : Safe_Str__Text                    = 'latest'               # diniscruz/sg-playwright:<tag>
    with_mitmproxy  : bool                              = False                  # 3rd container + proxy wiring
    intercept_script: Safe_Str__Vault_Path              = ''                     # vault path / inline script; meaningful only with with_mitmproxy
    public_ingress  : bool                              = False                  # True → :8000 opens 0.0.0.0/0 instead of caller /32
    registry        : Safe_Str__Text                    = ''                     # ECR registry host for the host-control image (empty → resolved)
