# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Captured
# The request fields L1 saw, in the snake_case shape the JS engine emits.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                          import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str                                           import Safe_Str

from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Method         import Safe_Str__Sentinel__Method
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Path           import Safe_Str__Sentinel__Path
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Host           import Safe_Str__Sentinel__Host
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__IP             import Safe_Str__Sentinel__IP
from sgraph_ai_service_playwright__cli.sentinel.primitives.Safe_Str__Sentinel__Timestamp      import Safe_Str__Sentinel__Timestamp


class Schema__Sentinel__Captured(Type_Safe):
    method       : Safe_Str__Sentinel__Method
    path         : Safe_Str__Sentinel__Path
    host         : Safe_Str__Sentinel__Host
    source_ip    : Safe_Str__Sentinel__IP
    user_agent   : Safe_Str
    querystring  : Safe_Str
    received_at  : Safe_Str__Sentinel__Timestamp
    cache_status : Safe_Str                                                                    # 'miss' for the MVP (cache disabled)
