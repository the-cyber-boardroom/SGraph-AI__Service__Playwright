# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Ec2__Create__Response
# Response for POST /v1/ec2/instances. Carries everything the CLI renders in
# the "Instance launched" panel, plus the preflight summary so callers know
# which account/region/registry/images were used.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Deploy_Name         import Safe_Str__Deploy_Name
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Stage               import Safe_Str__Stage
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_UInt__Max_Hours          import Safe_UInt__Max_Hours
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Preflight           import Schema__Ec2__Preflight


class Schema__Ec2__Create__Response(Type_Safe):
    instance_id         : Safe_Str__Instance__Id
    deploy_name         : Safe_Str__Deploy_Name
    stage               : Safe_Str__Stage
    creator             : Safe_Str__Id
    ami_id              : Safe_Str__AMI__Id
    public_ip           : Safe_Str__Text                                            # IPv4 string (empty before AWS assigns); Safe_Str__Text keeps dots intact
    playwright_url      : Safe_Str__Text                                            # http://<ip>:<port> — Safe_Str__Text preserves the full URL without scheme-regex burden
    sidecar_admin_url   : Safe_Str__Text
    browser_url         : Safe_Str__Text
    playwright_image_uri: Safe_Str__Text                                            # Full ECR URI — see Schema__Ec2__Preflight for rationale
    sidecar_image_uri   : Safe_Str__Text
    api_key_name        : Safe_Str__Id
    api_key_value       : Safe_Str__Id                                              # Returned once on create; never persisted server-side
    max_hours           : Safe_UInt__Max_Hours = 1
    preflight           : Schema__Ec2__Preflight
