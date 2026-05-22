# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Schema__Bedrock__Chat__Document
# A file attached to a chat message; Nova reads it via a Converse `document` block.
# data is base64 (Type_Safe-safe); the raw bytes are decoded when the block is built.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Bedrock__Chat__Document(Type_Safe):
    name     : str                                                                # document name (sanitised for Bedrock)
    format   : str                                                                # pdf | csv | doc | docx | xls | xlsx | html | txt | md
    size     : int                                                                # raw byte count (for the chip + cost hint)
    data_b64 : str                                                                # base64 of the file bytes
