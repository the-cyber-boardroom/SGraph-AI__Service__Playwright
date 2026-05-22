# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Schema__Bedrock__Chat__Tool_Call
# One tool the model invoked inside an agentic turn (for the Inspector). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Bedrock__Chat__Tool_Call(Type_Safe):
    name        : str                                                             # the toolUse name the model called
    input_json  : str                                                             # the input it passed (JSON)
    status      : str                                                             # 'success' | 'error'
    result_json : str                                                             # the toolResult payload (JSON, capped)
