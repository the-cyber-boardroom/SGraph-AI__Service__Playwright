# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Tui_Api__Params__Needle
# Params for blocks_why: a request id, or a source IP (raw or hashed). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Sentinel__Tui_Api__Params__Needle(Type_Safe):
    needle : str                                                                     # request id or source IP (raw / hashed)
