# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Firefox__Set__Interceptor__Response
# Returned by set_interceptor — confirms whether the live script update landed.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.firefox.primitives.Safe_Str__Firefox__Stack__Name import Safe_Str__Firefox__Stack__Name


class Schema__Firefox__Set__Interceptor__Response(Type_Safe):
    stack_name        : Safe_Str__Firefox__Stack__Name
    instance_id       : Safe_Str__Instance__Id
    interceptor_label : Safe_Str__Text                                               # 'none' / example name / 'inline'
    success           : bool         = False
    message           : Safe_Str__Text
    elapsed_ms        : int          = 0
