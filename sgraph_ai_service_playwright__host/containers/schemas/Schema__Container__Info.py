# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Container__Info
# Per-container status returned by GET /containers/{name}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Container__Info(Type_Safe):
    name       : str   # container name
    image      : str
    status     : str   # running | exited | created | ...
    state      : str   # Up 2 hours | Exited (0) 3 minutes ago
    ports      : dict  # { "8080/tcp": [{"HostPort": "8080"}] }
    created_at : str   # ISO-8601
    type_id    : str   # plugin type: docker | firefox | elastic | ...
