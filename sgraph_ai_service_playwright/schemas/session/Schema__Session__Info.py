# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Schema__Session__Info (spec §5.5)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt
from osbot_utils.type_safe.primitives.domains.identifiers.safe_int.Timestamp_Now                    import Timestamp_Now

from sgraph_ai_service_playwright.schemas.enums.Enum__Browser__Name                                 import Enum__Browser__Name
from sgraph_ai_service_playwright.schemas.enums.Enum__Session__Status                               import Enum__Session__Status
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Safe_Str__Trace_Id                 import Safe_Str__Trace_Id
from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                         import Session_Id


class Schema__Session__Info(Type_Safe):                                             # Lightweight session description
    session_id              : Session_Id
    status                  : Enum__Session__Status
    created_at              : Timestamp_Now
    last_activity_at        : Timestamp_Now                                         # Updated on every action
    expires_at              : Timestamp_Now                                         # created_at + lifetime_ms
    trace_id                : Safe_Str__Trace_Id
    browser_name            : Enum__Browser__Name
    total_actions           : Safe_UInt                                             # Cumulative count
    artefacts_captured      : Safe_UInt                                             # Cumulative count
