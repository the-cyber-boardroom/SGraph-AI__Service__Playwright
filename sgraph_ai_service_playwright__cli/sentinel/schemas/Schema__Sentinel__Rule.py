# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Rule
# Metadata registry entry for one MVP rule. Rule *logic* lives in JS
# (runtime/layer1/sentinel_l1.js); this is the Python-side description only.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str                                      import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action             import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Layer              import Enum__Sentinel__Layer
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Name      import Safe_Str__Sentinel__Name
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Rule_Id   import Safe_Str__Sentinel__Rule_Id


class Schema__Sentinel__Rule(Type_Safe):
    rule_id     : Safe_Str__Sentinel__Rule_Id
    name        : Safe_Str__Sentinel__Name
    layer       : Enum__Sentinel__Layer    = Enum__Sentinel__Layer.L1
    attack_tag  : Safe_Str                                                          # MITRE technique, e.g. 'T1190'
    confidence  : Safe_Str                                                          # 'deterministic-certain'
    action      : Enum__Sentinel__Action   = Enum__Sentinel__Action.PASS
    description : Safe_Str
