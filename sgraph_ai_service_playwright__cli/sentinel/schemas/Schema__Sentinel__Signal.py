# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Signal
# THE parity spine. L1 (JS) emits this exact shape (snake_case keys); L2 (Python)
# deserialises + validates it before acting. Byte-identical across all three
# targets — transport differs (header on AWS, in-process locally), schema does not.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str                                           import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict                 import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action                  import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Layer                   import Enum__Sentinel__Layer
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Request_Id     import Safe_Str__Sentinel__Request_Id
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Reason         import Safe_Str__Sentinel__Reason
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Rule_Id        import Safe_Str__Sentinel__Rule_Id
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Version        import Safe_Str__Sentinel__Version
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Captured            import Schema__Sentinel__Captured


class Schema__Sentinel__Signal(Type_Safe):
    request_id      : Safe_Str__Sentinel__Request_Id
    aws_request_id  : Safe_Str
    captured        : Schema__Sentinel__Captured
    verdict         : Enum__Sentinel__Verdict     = Enum__Sentinel__Verdict.ALLOW
    reason          : Safe_Str__Sentinel__Reason
    rule_id         : Safe_Str__Sentinel__Rule_Id
    action          : Enum__Sentinel__Action      = Enum__Sentinel__Action.PASS
    layer           : Enum__Sentinel__Layer       = Enum__Sentinel__Layer.L1
    engine_version  : Safe_Str__Sentinel__Version
    ruleset_version : Safe_Str__Sentinel__Version
