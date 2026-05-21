# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: List__CF_TUI__Field_Row
# Typed list of Schema__CF_TUI__Field_Row. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Field_Row import Schema__CF_TUI__Field_Row


class List__CF_TUI__Field_Row(Type_Safe__List):
    expected_type = Schema__CF_TUI__Field_Row
