# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Pod__Runtime__Factory
# Returns the appropriate Pod__Runtime adapter based on which CLI binary
# is available on the host. Docker is preferred; Podman is the fallback.
# ═══════════════════════════════════════════════════════════════════════════════

import shutil

from sg_compute.host_plane.pods.service.Pod__Runtime          import Pod__Runtime
from sg_compute.host_plane.pods.service.Pod__Runtime__Docker  import Pod__Runtime__Docker
from sg_compute.host_plane.pods.service.Pod__Runtime__Podman  import Pod__Runtime__Podman


def get_pod_runtime() -> Pod__Runtime:
    if shutil.which('docker'):
        return Pod__Runtime__Docker()
    if shutil.which('podman'):
        return Pod__Runtime__Podman()
    raise RuntimeError('no pod runtime found: neither docker nor podman is in PATH')
