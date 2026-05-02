# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Containers
# CRUD surface for containers on this EC2 host. Zero logic — pure delegation
# to the Container__Runtime returned by get_container_runtime().
#
# GET    /containers                  → Schema__Container__List
# POST   /containers                  → Schema__Container__Start__Response
# GET    /containers/{name}           → Schema__Container__Info   (404 on miss)
# GET    /containers/{name}/logs      → Schema__Container__Logs__Response
# POST   /containers/{name}/stop      → Schema__Container__Stop__Response
# DELETE /containers/{name}           → Schema__Container__Stop__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                             import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                         import Fast_API__Routes

from sgraph_ai_service_playwright__host.containers.schemas.Schema__Container__Start__Request  import Schema__Container__Start__Request
from sgraph_ai_service_playwright__host.containers.service.Container__Runtime__Factory  import get_container_runtime

TAG__ROUTES_HOST_CONTAINERS = 'containers'


class Routes__Host__Containers(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_CONTAINERS

    def list_containers(self) -> dict:                                              # GET /containers
        return get_container_runtime().list().json()
    list_containers.__route_path__ = '/list'

    def start_container(self, body: Schema__Container__Start__Request) -> dict:    # POST /containers
        return get_container_runtime().start(body).json()
    start_container.__route_path__ = ''

    def get_container(self, name: str) -> dict:                                    # GET /containers/{name}
        result = get_container_runtime().info(name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'container {name!r} not found')
        return result.json()
    get_container.__route_path__ = '/{name}'

    def get_logs(self, name: str, tail: int = 100) -> dict:                        # GET /containers/{name}/logs
        return get_container_runtime().logs(name, tail).json()
    get_logs.__route_path__ = '/{name}/logs'

    def stop_container(self, name: str) -> dict:                                   # POST /containers/{name}/stop
        return get_container_runtime().stop(name).json()
    stop_container.__route_path__ = '/{name}/stop'

    def remove_container(self, name: str) -> dict:                                 # DELETE /containers/{name}
        return get_container_runtime().remove(name).json()
    remove_container.__route_path__ = '/{name}'

    def setup_routes(self):
        self.add_route_get   (self.list_containers )
        self.add_route_post  (self.start_container )
        self.add_route_get   (self.get_container   )
        self.add_route_get   (self.get_logs        )
        self.add_route_post  (self.stop_container  )
        self.add_route_delete(self.remove_container)
