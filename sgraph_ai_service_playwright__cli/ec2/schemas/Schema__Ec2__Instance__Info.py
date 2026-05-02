# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Ec2__Instance__Info
# Response for GET /v1/ec2/instances/{target}. Mirrors the dict built by
# scripts.provision_ec2.cmd_info. Image URIs live in the on-instance compose
# file, not in tags — that's why the fields carry a sentinel string on info.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.ec2.enums.Enum__Instance__State              import Enum__Instance__State
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Deploy_Name         import Safe_Str__Deploy_Name
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Stage               import Safe_Str__Stage


class Schema__Ec2__Instance__Info(Type_Safe):
    instance_id         : Safe_Str__Instance__Id
    deploy_name         : Safe_Str__Deploy_Name
    stage               : Safe_Str__Stage
    creator             : Safe_Str__Id
    ami_id              : Safe_Str__AMI__Id
    public_ip           : Safe_Str__Text                                            # IPv4 dotted quad — Safe_Str__Id would mangle the dots
    playwright_url      : Safe_Str__Text
    sidecar_admin_url   : Safe_Str__Text
    browser_url         : Safe_Str__Text
    api_key_name        : Safe_Str__Id
    api_key_value       : Safe_Str__Id                                              # From the instance tags; same value the create call returned
    playwright_image_uri: Safe_Str__Text                                            # Sentinel "(stored in compose file on instance)" until tags carry the URI
    sidecar_image_uri   : Safe_Str__Text
    instance_type            : Safe_Str__Text                                       # Recorded at create time from sg:instance-type tag (preserves dot in 'm6i.xlarge')
    state                    : Enum__Instance__State = Enum__Instance__State.UNKNOWN
    host_api_url             : Safe_Str__Text                                       # "http://{public_ip}:9000" — empty until boot complete
    host_api_key_vault_path  : Safe_Str__Text                                       # "/ec2/{deploy_name}/host-api-key" — empty until provisioned
