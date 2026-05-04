# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Pod__Info
# Per-pod status returned by GET /pods/{name}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Pod__Info(Type_Safe):
    name       : str   # pod name
    image      : str
    status     : str   # running | exited | created | ...
    state      : str   # Up 2 hours | Exited (0) 3 minutes ago
    ports      : dict  # { "8080/tcp": [{"HostPort": "8080"}] }
    created_at : str   # ISO-8601
    type_id    : str   # plugin type: docker | firefox | elastic | ...
