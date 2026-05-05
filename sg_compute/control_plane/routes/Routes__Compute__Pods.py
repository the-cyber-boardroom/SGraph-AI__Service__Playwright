# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__Pods
# Pod management endpoints — proxies via Pod__Manager to each Node's sidecar.
#
# Endpoints (all under /api/nodes prefix)
# ─────────────────────────────────────
#   GET    /api/nodes/{node_id}/pods/list        → Schema__Pod__List
#   POST   /api/nodes/{node_id}/pods             → Schema__Pod__Info
#   GET    /api/nodes/{node_id}/pods/{name}      → Schema__Pod__Info (404 on miss)
#   GET    /api/nodes/{node_id}/pods/{name}/logs → Schema__Pod__Logs__Response
#   POST   /api/nodes/{node_id}/pods/{name}/stop → Schema__Pod__Stop__Response
#   DELETE /api/nodes/{node_id}/pods/{name}      → Schema__Pod__Stop__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                   import HTTPException
from osbot_fast_api.api.routes.Fast_API__Routes                               import Fast_API__Routes

from sg_compute.core.pod.Pod__Manager                                         import Pod__Manager
from sg_compute.core.pod.schemas.Schema__Pod__Start__Request                  import Schema__Pod__Start__Request

TAG__ROUTES_COMPUTE_PODS = 'pods'


class Routes__Compute__Pods(Fast_API__Routes):
    tag     : str         = TAG__ROUTES_COMPUTE_PODS
    prefix  : str         = '/api/nodes'
    manager : Pod__Manager

    def list_pods(self, node_id: str) -> dict:                               # GET /{node_id}/pods/list
        return self.manager.list_pods(node_id).json()
    list_pods.__route_path__ = '/{node_id}/pods/list'

    def start_pod(self, node_id: str, body: Schema__Pod__Start__Request) -> dict:  # POST /{node_id}/pods
        return self.manager.start_pod(node_id, body).json()
    start_pod.__route_path__ = '/{node_id}/pods'

    def get_pod(self, node_id: str, name: str) -> dict:                      # GET /{node_id}/pods/{name}
        pod = self.manager.get_pod(node_id, name)
        if pod is None:
            raise HTTPException(status_code=404, detail=f'pod {name!r} not found on node {node_id!r}')
        return pod.json()
    get_pod.__route_path__ = '/{node_id}/pods/{name}'

    def get_pod_logs(self, node_id: str, name: str,                          # GET /{node_id}/pods/{name}/logs
                     tail: int = 100, timestamps: bool = False) -> dict:
        return self.manager.get_pod_logs(node_id, name, tail=tail, timestamps=timestamps).json()
    get_pod_logs.__route_path__ = '/{node_id}/pods/{name}/logs'

    def stop_pod(self, node_id: str, name: str) -> dict:                     # POST /{node_id}/pods/{name}/stop
        return self.manager.stop_pod(node_id, name).json()
    stop_pod.__route_path__ = '/{node_id}/pods/{name}/stop'

    def remove_pod(self, node_id: str, name: str) -> dict:                   # DELETE /{node_id}/pods/{name}
        return self.manager.remove_pod(node_id, name).json()
    remove_pod.__route_path__ = '/{node_id}/pods/{name}'

    def setup_routes(self):
        self.add_route_get   (self.list_pods   )
        self.add_route_post  (self.start_pod   )
        self.add_route_get   (self.get_pod     )
        self.add_route_get   (self.get_pod_logs)
        self.add_route_post  (self.stop_pod    )
        self.add_route_delete(self.remove_pod  )
