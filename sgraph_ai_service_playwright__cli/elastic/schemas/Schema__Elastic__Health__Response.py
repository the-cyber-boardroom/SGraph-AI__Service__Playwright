# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__Health__Response
# Full result of `sp elastic health`: a header (stack name + an "all OK"
# rollup) plus the ordered list of per-check results.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Health__Check import List__Schema__Elastic__Health__Check
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name


class Schema__Elastic__Health__Response(Type_Safe):
    stack_name : Safe_Str__Elastic__Stack__Name
    all_ok     : bool                                = False                        # True when every check is OK or SKIP — a single FAIL flips it false
    checks     : List__Schema__Elastic__Health__Check
