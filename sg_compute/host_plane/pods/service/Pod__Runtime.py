# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Pod__Runtime
# Abstract base defining the pod management interface.
# Docker and Podman adapters implement this by shelling out to the CLI.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                        import Type_Safe

from sg_compute.host_plane.pods.schemas.Schema__Pod__Info                   import Schema__Pod__Info
from sg_compute.host_plane.pods.schemas.Schema__Pod__List                   import Schema__Pod__List
from sg_compute.host_plane.pods.schemas.Schema__Pod__Logs__Response         import Schema__Pod__Logs__Response
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Request         import Schema__Pod__Start__Request
from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Response        import Schema__Pod__Start__Response
from sg_compute.host_plane.pods.schemas.Schema__Pod__Stop__Response         import Schema__Pod__Stop__Response


class Pod__Runtime(Type_Safe):

    def list(self) -> Schema__Pod__List:                                    # GET /pods
        raise NotImplementedError

    def start(self, req: Schema__Pod__Start__Request) -> Schema__Pod__Start__Response:
        raise NotImplementedError                                            # POST /pods

    def info(self, name: str) -> Schema__Pod__Info | None:                  # GET /pods/{name} — None → 404
        raise NotImplementedError

    def logs(self, name: str, tail: int = 100) -> Schema__Pod__Logs__Response:
        raise NotImplementedError                                            # GET /pods/{name}/logs

    def stop(self, name: str) -> Schema__Pod__Stop__Response:               # POST /pods/{name}/stop
        raise NotImplementedError

    def remove(self, name: str) -> Schema__Pod__Stop__Response:             # DELETE /pods/{name}
        raise NotImplementedError
