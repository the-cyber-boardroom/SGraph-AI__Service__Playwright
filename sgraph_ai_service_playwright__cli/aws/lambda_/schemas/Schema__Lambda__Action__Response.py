# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lambda__Action__Response
# Generic response for delete and URL management operations.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name     import Safe_Str__Lambda__Name


class Schema__Lambda__Action__Response(Type_Safe):
    name    : Safe_Str__Lambda__Name
    success : bool = False
    message : str  = ''
