# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/bedrock/tui/tui_api: Schema__Chat__Params__Set_Model
# Params for the chat 'set_model' action (Nova alias). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Chat__Params__Set_Model(Type_Safe):
    alias : str                                                                   # Nova alias: default | lite | micro | pro | premier
