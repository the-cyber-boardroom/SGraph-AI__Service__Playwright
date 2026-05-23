# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Tui_Api__Params__Repeat
# Params for traffic_gen: how many times to replay the corpus. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Sentinel__Tui_Api__Params__Repeat(Type_Safe):
    repeat : int = 1                                                                 # corpus replays (>=1)
