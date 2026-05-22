# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Tool_Call (neutral)
# One tool the model invoked in an agentic turn (for the Inspector / tool-call card).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Chat__Tool_Call(Type_Safe):
    name        : str
    input_json  : str
    status      : str
    result_json : str
