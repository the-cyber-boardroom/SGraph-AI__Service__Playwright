# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: List__CF_TUI__Series_Point
# Typed list of Schema__CF_TUI__Series_Point. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Series_Point import Schema__CF_TUI__Series_Point


class List__CF_TUI__Series_Point(Type_Safe__List):
    expected_type = Schema__CF_TUI__Series_Point
