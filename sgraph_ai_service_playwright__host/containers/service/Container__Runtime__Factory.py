# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Container__Runtime__Factory
# Returns the appropriate Container__Runtime adapter based on which CLI binary
# is available on the host. Docker is preferred; Podman is the fallback.
# ═══════════════════════════════════════════════════════════════════════════════

import shutil

from sgraph_ai_service_playwright__host.containers.service.Container__Runtime          import Container__Runtime
from sgraph_ai_service_playwright__host.containers.service.Container__Runtime__Docker  import Container__Runtime__Docker
from sgraph_ai_service_playwright__host.containers.service.Container__Runtime__Podman  import Container__Runtime__Podman


def get_container_runtime() -> Container__Runtime:
    if shutil.which('docker'):
        return Container__Runtime__Docker()
    if shutil.which('podman'):
        return Container__Runtime__Podman()
    raise RuntimeError('no container runtime found: neither docker nor podman is in PATH')
