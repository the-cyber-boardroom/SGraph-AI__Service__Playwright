# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI observe — Schema__Observe__Source__Status
# Status record for a single observability source adapter.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.observe.primitives.Safe_Str__Observe__Event_Time  import Safe_Str__Observe__Event_Time
from sgraph_ai_service_playwright__cli.aws.observe.primitives.Safe_Str__Observe__Source_Name import Safe_Str__Observe__Source_Name


class Schema__Observe__Source__Status(Type_Safe):
    name         : Safe_Str__Observe__Source_Name
    connected    : bool = False
    stream_count : int  = 0
    last_event   : Safe_Str__Observe__Event_Time
