# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Host__Status
# Returned by GET /host/status. Populated via psutil on the host.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Host__Status(Type_Safe):
    cpu_percent     : float = 0.0
    mem_total_mb    : int   = 0
    mem_used_mb     : int   = 0
    disk_total_gb   : int   = 0
    disk_used_gb    : int   = 0
    uptime_seconds  : int   = 0
    container_count : int   = 0
