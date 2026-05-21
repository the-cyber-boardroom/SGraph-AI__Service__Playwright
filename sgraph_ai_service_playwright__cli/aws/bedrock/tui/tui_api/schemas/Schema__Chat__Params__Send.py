# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/bedrock/tui/tui_api: Schema__Chat__Params__Send
# Params for the chat 'send' action. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Chat__Params__Send(Type_Safe):
    text : str                                                                    # the user message to send to the model
