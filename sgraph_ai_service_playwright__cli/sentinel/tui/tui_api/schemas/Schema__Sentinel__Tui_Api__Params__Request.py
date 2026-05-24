# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Tui_Api__Params__Request
# Params for request-id-targeting actions (logs_trace). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Sentinel__Tui_Api__Params__Request(Type_Safe):
    request_id : str                                                                 # e.g. 'sn-ab12…'
