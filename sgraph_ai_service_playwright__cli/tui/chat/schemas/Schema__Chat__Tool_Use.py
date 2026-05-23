# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Tool_Use (neutral)
# The model's request to call a tool. Backends adapt to/from their wire shape
# (Bedrock toolUse / OpenAI tool_calls). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Chat__Tool_Use(Type_Safe):
    id    : str                                                                   # correlation id (toolUseId / tool_call.id)
    name  : str                                                                   # the (neutral, sanitised) tool name
    input : dict                                                                  # the arguments the model passed
