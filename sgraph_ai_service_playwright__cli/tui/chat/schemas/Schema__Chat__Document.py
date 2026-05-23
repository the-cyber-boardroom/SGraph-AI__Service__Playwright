# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Document (neutral)
# A document attached to a message; backends adapt it to their wire shape (Bedrock
# document block / OpenAI). data is base64. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Chat__Document(Type_Safe):
    name     : str
    format   : str
    size     : int
    data_b64 : str
