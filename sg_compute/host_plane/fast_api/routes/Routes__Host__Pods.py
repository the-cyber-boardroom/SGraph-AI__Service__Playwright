# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Pods
# CRUD surface for pods on this EC2 host. Zero logic — pure delegation
# to the Pod__Runtime returned by get_pod_runtime().
#
# GET    /pods/list              → Schema__Pod__List
# POST   /pods                   → Schema__Pod__Start__Response
# GET    /pods/{name}            → Schema__Pod__Info   (404 on miss)
# GET    /pods/{name}/logs       → Schema__Pod__Logs__Response  (404 on miss)
# GET    /pods/{name}/stats      → Schema__Pod__Stats           (404 on miss)
# POST   /pods/{name}/stop       → Schema__Pod__Stop__Response
# DELETE /pods/{name}            → Schema__Pod__Stop__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                    import HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                import Fast_API__Routes

from sg_compute.host_plane.pods.schemas.Schema__Pod__Start__Request            import Schema__Pod__Start__Request
from sg_compute.host_plane.pods.service.Pod__Runtime__Factory                  import get_pod_runtime

TAG__ROUTES_HOST_PODS = 'pods'


class Routes__Host__Pods(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_PODS

    def list_pods(self) -> dict:                                            # GET /pods/list
        return get_pod_runtime().list().json()
    list_pods.__route_path__ = '/list'

    def start_pod(self, body: Schema__Pod__Start__Request) -> dict:        # POST /pods
        return get_pod_runtime().start(body).json()
    start_pod.__route_path__ = ''

    def get_pod(self, name: str) -> dict:                                  # GET /pods/{name}
        result = get_pod_runtime().info(name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'pod {name!r} not found')
        return result.json()
    get_pod.__route_path__ = '/{name}'

    def get_logs(self, name: str, tail: int = 100,                         # GET /pods/{name}/logs
                 timestamps: bool = False) -> dict:
        result = get_pod_runtime().logs(name, tail=tail, timestamps=timestamps)
        if result is None:
            raise HTTPException(status_code=404, detail=f'pod {name!r} not found')
        return result.json()
    get_logs.__route_path__ = '/{name}/logs'

    def get_stats(self, name: str) -> dict:                                # GET /pods/{name}/stats
        result = get_pod_runtime().stats(name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'pod {name!r} not found')
        return result.json()
    get_stats.__route_path__ = '/{name}/stats'

    def stop_pod(self, name: str) -> dict:                                 # POST /pods/{name}/stop
        return get_pod_runtime().stop(name).json()
    stop_pod.__route_path__ = '/{name}/stop'

    def remove_pod(self, name: str) -> dict:                               # DELETE /pods/{name}
        return get_pod_runtime().remove(name).json()
    remove_pod.__route_path__ = '/{name}'

    def setup_routes(self):
        self.add_route_get   (self.list_pods  )
        self.add_route_post  (self.start_pod  )
        self.add_route_get   (self.get_pod    )
        self.add_route_get   (self.get_logs   )
        self.add_route_get   (self.get_stats  )
        self.add_route_post  (self.stop_pod   )
        self.add_route_delete(self.remove_pod )
