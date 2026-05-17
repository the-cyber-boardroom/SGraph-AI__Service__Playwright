# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__CF__Action__Response
# Generic response for disable / delete / wait operations.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Distribution_Id  import Safe_Str__CF__Distribution_Id


class Schema__CF__Action__Response(Type_Safe):
    distribution_id : Safe_Str__CF__Distribution_Id
    success         : bool = False
    message         : str  = ''
