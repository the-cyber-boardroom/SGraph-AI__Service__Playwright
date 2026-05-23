# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Tool (neutral)
# A tool offered to the model. name is sanitised to [a-zA-Z0-9_-]{1,64} (valid for
# Bedrock AND OpenAI). Backends wrap the SHAPE (toolConfig / tools[]); never the name.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Chat__Tool(Type_Safe):
    name         : str
    description  : str
    input_schema : dict                                                           # JSON Schema (from Tui_Api__Schema__Builder)
