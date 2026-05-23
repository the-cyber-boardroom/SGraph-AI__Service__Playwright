# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Traffic__Case
# One use-case request in the traffic corpus: what to send and what we expect SG/
# Sentinel to decide. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                  import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict         import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__IP     import Safe_Str__Sentinel__IP
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Method import Safe_Str__Sentinel__Method
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Name   import Safe_Str__Sentinel__Name
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Path   import Safe_Str__Sentinel__Path
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Rule_Id import Safe_Str__Sentinel__Rule_Id
from sgraph_ai_service_playwright__cli.sentinel.traffic.enums.Enum__Traffic__Category import Enum__Traffic__Category


class Schema__Traffic__Case(Type_Safe):
    name             : Safe_Str__Sentinel__Name
    method           : Safe_Str__Sentinel__Method
    path             : Safe_Str__Sentinel__Path
    source_ip        : Safe_Str__Sentinel__IP
    category         : Enum__Traffic__Category = Enum__Traffic__Category.BENIGN
    expected_verdict : Enum__Sentinel__Verdict = Enum__Sentinel__Verdict.ALLOW
    expected_rule    : Safe_Str__Sentinel__Rule_Id
