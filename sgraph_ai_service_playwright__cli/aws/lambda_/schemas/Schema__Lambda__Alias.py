# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lambda__Alias
# One Lambda alias. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name


class Schema__Lambda__Alias(Type_Safe):
    name            : Safe_Str__Lambda__Name
    alias_name      : str = ''
    function_version: str = ''
    description     : str = ''
