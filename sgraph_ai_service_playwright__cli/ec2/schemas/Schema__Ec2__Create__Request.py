# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Ec2__Create__Request
# Inputs for POST /v1/ec2/instances. All fields are optional — the service
# fills in sensible defaults (env vars, random deploy name, default images)
# matching the `sp create` CLI behaviour.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Deploy_Name         import Safe_Str__Deploy_Name
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Stage               import Safe_Str__Stage
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_UInt__Max_Hours          import Safe_UInt__Max_Hours


class Schema__Ec2__Create__Request(Type_Safe):
    stage               : Safe_Str__Stage       = 'dev'
    deploy_name         : Safe_Str__Deploy_Name = ''                                # Empty → service generates a random name
    playwright_image_uri: Safe_Str__Text         = ''                               # Empty → default ECR URI resolved by service
    sidecar_image_uri   : Safe_Str__Text         = ''                               # Empty → default ECR URI resolved by service
    from_ami            : Safe_Str__AMI__Id      = ''                               # Pre-baked AMI; empty → latest AL2023 resolved by service
    instance_type       : Safe_Str__Id           = ''                               # Empty → default from scripts.provision_ec2.EC2__INSTANCE_TYPE
    max_hours           : Safe_UInt__Max_Hours  = 1                                 # 0 = no auto-delete
    upstream_url        : Safe_Str__Text         = ''                               # mitmproxy upstream (empty = direct mode); URL scheme kept intact
    upstream_user       : Safe_Str__Id           = ''
    upstream_pass       : Safe_Str__Text         = ''                               # Passwords may contain punctuation; Safe_Str__Text preserves it
    http2               : Safe_Str__Id           = ''                               # 'false' disables HTTP/2 on the sidecar; empty = service default
