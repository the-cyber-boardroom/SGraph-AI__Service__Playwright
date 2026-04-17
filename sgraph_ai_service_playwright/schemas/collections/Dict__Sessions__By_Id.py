# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Dict__Sessions__By_Id (spec §6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__Dict                               import Type_Safe__Dict

from sgraph_ai_service_playwright.schemas.primitives.identifiers.Session_Id                         import Session_Id
from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                             import Schema__Session__Info


class Dict__Sessions__By_Id(Type_Safe__Dict):                                       # Active sessions in memory
    expected_key_type   = Session_Id
    expected_value_type = Schema__Session__Info
