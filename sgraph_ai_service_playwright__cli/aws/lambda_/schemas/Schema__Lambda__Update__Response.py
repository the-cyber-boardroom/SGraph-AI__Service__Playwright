# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lambda__Update__Response
# Result of update_function_configuration.  Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name


class Schema__Lambda__Update__Response(Type_Safe):
    name    : Safe_Str__Lambda__Name
    success : bool = False
    message : str  = ''
