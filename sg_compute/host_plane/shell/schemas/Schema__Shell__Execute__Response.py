# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Shell__Execute__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Shell__Execute__Response(Type_Safe):
    stdout    : str
    stderr    : str
    exit_code : int   = 0
    duration  : float = 0.0
    timed_out : bool  = False
