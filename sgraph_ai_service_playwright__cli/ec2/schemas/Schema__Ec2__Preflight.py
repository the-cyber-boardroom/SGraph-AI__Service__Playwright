# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Ec2__Preflight
# Preflight summary shown at the top of `sp create` and echoed into the create
# response so callers know which account/region/registry/images were resolved.
# api_key_source tracks whether the key came from env or was generated.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AWS__Account_Id        import Safe_Str__AWS__Account_Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region  import Safe_Str__AWS__Region


class Schema__Ec2__Preflight(Type_Safe):
    aws_account         : Safe_Str__AWS__Account_Id
    aws_region          : Safe_Str__AWS__Region
    registry            : Safe_Str__Text                                            # ECR registry host — contains dots; Safe_Str__Id would sanitise them
    playwright_image_uri: Safe_Str__Text                                            # Full ECR image URI (host/name:tag) — dots + slashes + colons
    sidecar_image_uri   : Safe_Str__Text
    api_key_name        : Safe_Str__Id
    api_key_generated   : bool = False                                              # True when FAST_API__AUTH__API_KEY__VALUE was not set and a random one was minted
