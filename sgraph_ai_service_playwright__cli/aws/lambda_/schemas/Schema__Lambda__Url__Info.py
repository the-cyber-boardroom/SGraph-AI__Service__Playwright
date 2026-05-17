# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lambda__Url__Info
# Lambda Function URL configuration returned by get/create URL operations.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.enums.Enum__Lambda__Url__Auth_Type    import Enum__Lambda__Url__Auth_Type
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name     import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Url      import Safe_Str__Lambda__Url


class Schema__Lambda__Url__Info(Type_Safe):
    name          : Safe_Str__Lambda__Name
    function_url  : Safe_Str__Lambda__Url
    auth_type     : Enum__Lambda__Url__Auth_Type = Enum__Lambda__Url__Auth_Type.NONE
    exists        : bool = False
