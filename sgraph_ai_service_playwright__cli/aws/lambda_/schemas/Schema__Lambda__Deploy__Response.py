# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lambda__Deploy__Response
# Returned by Lambda__Deployer.deploy_from_folder().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Arn      import Safe_Str__Lambda__Arn
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name     import Safe_Str__Lambda__Name


class Schema__Lambda__Deploy__Response(Type_Safe):
    name         : Safe_Str__Lambda__Name
    function_arn : Safe_Str__Lambda__Arn
    created      : bool = False                                                           # True = new function; False = updated
    success      : bool = False
    message      : str  = ''
