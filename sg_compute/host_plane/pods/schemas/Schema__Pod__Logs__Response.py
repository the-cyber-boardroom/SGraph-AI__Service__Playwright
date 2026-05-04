# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Pod__Logs__Response
# Returned by GET /pods/{name}/logs.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Pod__Logs__Response(Type_Safe):
    container : str
    lines     : int  = 0      # actual number of lines returned
    content   : str           # stdout + stderr joined; drop into <pre> directly
    truncated : bool = False   # True when output was capped at the requested tail limit
