# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Host__Runtime
# Returned by GET /host/runtime. Identifies the container runtime and version.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Host__Runtime(Type_Safe):
    runtime : str   # docker | podman
    version : str   # version string from `docker version` / `podman version`
