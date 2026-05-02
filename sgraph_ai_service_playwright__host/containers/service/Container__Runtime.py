# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Container__Runtime
# Abstract base defining the container management interface.
# Docker and Podman adapters implement this by shelling out to the CLI.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__host.containers.schemas.Schema__Container__Info             import Schema__Container__Info
from sgraph_ai_service_playwright__host.containers.schemas.Schema__Container__List             import Schema__Container__List
from sgraph_ai_service_playwright__host.containers.schemas.Schema__Container__Logs__Response   import Schema__Container__Logs__Response
from sgraph_ai_service_playwright__host.containers.schemas.Schema__Container__Start__Request   import Schema__Container__Start__Request
from sgraph_ai_service_playwright__host.containers.schemas.Schema__Container__Start__Response  import Schema__Container__Start__Response
from sgraph_ai_service_playwright__host.containers.schemas.Schema__Container__Stop__Response   import Schema__Container__Stop__Response


class Container__Runtime(Type_Safe):

    def list(self) -> Schema__Container__List:                                      # GET /containers
        raise NotImplementedError

    def start(self, req: Schema__Container__Start__Request) -> Schema__Container__Start__Response:
        raise NotImplementedError                                                    # POST /containers

    def info(self, name: str) -> Schema__Container__Info | None:                    # GET /containers/{name} — None → 404
        raise NotImplementedError

    def logs(self, name: str, tail: int = 100) -> Schema__Container__Logs__Response:
        raise NotImplementedError                                                    # GET /containers/{name}/logs

    def stop(self, name: str) -> Schema__Container__Stop__Response:                 # POST /containers/{name}/stop
        raise NotImplementedError

    def remove(self, name: str) -> Schema__Container__Stop__Response:              # DELETE /containers/{name}
        raise NotImplementedError
