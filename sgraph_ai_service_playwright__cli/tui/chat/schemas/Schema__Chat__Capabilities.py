# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Schema__Chat__Capabilities (neutral)
# What a backend/model can do — the engine + screen gate on this (no tools → chat-only;
# no streaming → render whole reply; no documents → disable attach). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Chat__Capabilities(Type_Safe):
    streaming   : bool = True
    tools       : bool = False
    documents   : bool = False
    vision      : bool = False
    max_context : int  = 0
