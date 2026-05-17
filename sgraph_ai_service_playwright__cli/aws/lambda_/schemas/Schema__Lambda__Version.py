# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lambda__Version
# One published Lambda version. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name


class Schema__Lambda__Version(Type_Safe):
    name          : Safe_Str__Lambda__Name
    version       : str = ''
    description   : str = ''
    last_modified : str = ''
    code_size     : int = 0
