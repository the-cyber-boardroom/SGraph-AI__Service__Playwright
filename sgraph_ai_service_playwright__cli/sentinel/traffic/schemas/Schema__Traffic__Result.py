# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Traffic__Result
# The observed outcome of replaying one case (in-process or over HTTP). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                  import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict         import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Name   import Safe_Str__Sentinel__Name
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Rule_Id import Safe_Str__Sentinel__Rule_Id
from sgraph_ai_service_playwright__cli.sentinel.traffic.enums.Enum__Traffic__Category import Enum__Traffic__Category


class Schema__Traffic__Result(Type_Safe):
    name             : Safe_Str__Sentinel__Name
    category         : Enum__Traffic__Category = Enum__Traffic__Category.BENIGN
    expected_verdict : Enum__Sentinel__Verdict = Enum__Sentinel__Verdict.ALLOW
    observed_verdict : Enum__Sentinel__Verdict = Enum__Sentinel__Verdict.ALLOW
    expected_rule    : Safe_Str__Sentinel__Rule_Id
    observed_rule    : Safe_Str__Sentinel__Rule_Id
    http_status      : int   = 0                                                      # 0 in-process; real status over HTTP
    latency_ms       : float = 0.0
    matched          : bool  = False                                                  # observed verdict == expected verdict
