# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Schema__Tui_Api__Event
# One event a provider can emit (for the 'watch' surface). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Tui_Api__Event(Type_Safe):
    name           : str
    description    : str
    payload_schema : dict                                                         # free-form JSON Schema for the event payload
