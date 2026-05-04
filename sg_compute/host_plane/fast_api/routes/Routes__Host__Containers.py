# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Containers
# Container-centric aliases for the UI panel.  All delegation goes to the same
# Pod__Runtime returned by get_pod_runtime().
#
# GET  /containers/list          → Schema__Pod__List
# GET  /containers/{name}/logs   → Schema__Pod__Logs__Response  (404 on miss)
# GET  /containers/{name}/stats  → Schema__Pod__Stats           (404 on miss)
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                    import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                import Fast_API__Routes

from sg_compute.host_plane.pods.service.Pod__Runtime__Factory                  import get_pod_runtime

TAG__ROUTES_HOST_CONTAINERS = 'containers'


class Routes__Host__Containers(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_CONTAINERS

    def list_containers(self) -> dict:                                      # GET /containers/list
        return get_pod_runtime().list().json()
    list_containers.__route_path__ = '/list'

    def get_container_logs(self, name: str, lines: int = 100,              # GET /containers/{name}/logs
                           timestamps: bool = False) -> dict:
        result = get_pod_runtime().logs(name, tail=lines, timestamps=timestamps)
        if result is None:
            raise HTTPException(status_code=404, detail='container not found')
        return result.json()
    get_container_logs.__route_path__ = '/{name}/logs'

    def get_container_stats(self, name: str) -> dict:                      # GET /containers/{name}/stats
        result = get_pod_runtime().stats(name)
        if result is None:
            raise HTTPException(status_code=404, detail='container not found')
        return result.json()
    get_container_stats.__route_path__ = '/{name}/stats'

    def setup_routes(self):
        self.add_route_get(self.list_containers    )
        self.add_route_get(self.get_container_logs )
        self.add_route_get(self.get_container_stats)
