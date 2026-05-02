# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — SHELL_COMMAND_ALLOWLIST
# Shared between Safe_Str__Shell__Command (primitive validation) and
# Shell__Executor (double-checks at execution time). Deny-all by default —
# only these exact prefixes are permitted.
# ═══════════════════════════════════════════════════════════════════════════════

SHELL_COMMAND_ALLOWLIST: list[str] = [
    'docker ps', 'docker logs', 'docker stats', 'docker inspect',
    'podman ps', 'podman logs', 'podman stats', 'podman inspect',
    'df -h', 'free -m', 'uptime', 'uname -r',
    'cat /proc/meminfo', 'cat /proc/cpuinfo',
    'systemctl status',
]
