# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Log_Record
# What L2 writes to the sink (NDJSON-serialisable). Flattened from the signal plus
# the enforcement outcome and target; replayable. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str                                           import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action                  import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Layer                   import Enum__Sentinel__Layer
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Target                  import Enum__Sentinel__Target
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict                 import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Host           import Safe_Str__Sentinel__Host
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__IP             import Safe_Str__Sentinel__IP
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Method         import Safe_Str__Sentinel__Method
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Path           import Safe_Str__Sentinel__Path
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Reason         import Safe_Str__Sentinel__Reason
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Request_Id     import Safe_Str__Sentinel__Request_Id
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Rule_Id        import Safe_Str__Sentinel__Rule_Id
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Timestamp      import Safe_Str__Sentinel__Timestamp


class Schema__Sentinel__Log_Record(Type_Safe):
    request_id      : Safe_Str__Sentinel__Request_Id
    received_at     : Safe_Str__Sentinel__Timestamp
    target          : Enum__Sentinel__Target      = Enum__Sentinel__Target.LOCAL_DIRECT
    method          : Safe_Str__Sentinel__Method
    path            : Safe_Str__Sentinel__Path
    host            : Safe_Str__Sentinel__Host
    source_ip       : Safe_Str__Sentinel__IP                                                   # subject to privacy mode
    user_agent      : Safe_Str
    verdict         : Enum__Sentinel__Verdict     = Enum__Sentinel__Verdict.ALLOW
    reason          : Safe_Str__Sentinel__Reason
    rule_id         : Safe_Str__Sentinel__Rule_Id
    action          : Enum__Sentinel__Action      = Enum__Sentinel__Action.PASS
    layer           : Enum__Sentinel__Layer       = Enum__Sentinel__Layer.L1
    enforced        : bool                         = False
    http_status     : int                          = 0
    engine_version  : Safe_Str
    ruleset_version : Safe_Str
