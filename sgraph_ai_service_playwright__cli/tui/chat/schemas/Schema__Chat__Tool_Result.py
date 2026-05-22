# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Tool_Result (neutral)
# The outcome fed back to the model after a tool runs (honestly — gated/failed too).
# Backends adapt to their wire shape (Bedrock toolResult / OpenAI tool message).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Chat__Tool_Result(Type_Safe):
    id     : str                                                                  # matches the tool_use id
    status : str                                                                  # 'success' | 'error'
    data   : dict                                                                 # the result payload (or {error, dry_run, preview})
