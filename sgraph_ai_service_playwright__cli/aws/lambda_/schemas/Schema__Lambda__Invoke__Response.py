# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Lambda__Invoke__Response
# Result of a Lambda synchronous or async invocation. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name


class Schema__Lambda__Invoke__Response(Type_Safe):
    name          : Safe_Str__Lambda__Name
    status_code   : int  = 0
    payload       : str  = ''    # decoded JSON string
    function_error: str  = ''    # set when Lambda returns a function error
    log_tail      : str  = ''    # last 4KB of execution log (if LogType=Tail)
    success       : bool = False
    message       : str  = ''
