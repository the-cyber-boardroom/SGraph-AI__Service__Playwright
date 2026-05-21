# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui debug: List__Debug_Event
# Typed list of Schema__Debug_Event. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.tui.debug.Schema__Debug_Event import Schema__Debug_Event


class List__Debug_Event(Type_Safe__List):
    expected_type = Schema__Debug_Event
