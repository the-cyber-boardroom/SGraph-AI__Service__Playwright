# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Compute__Pods
# Pod management endpoints — proxies via Pod__Manager to each Node's sidecar.
#
# Endpoints (all under /api/nodes prefix)
# ─────────────────────────────────────
#   GET    /api/nodes/{node_id}/pods/list         → Schema__Pod__List
#   POST   /api/nodes/{node_id}/pods              → Schema__Pod__Info
#   GET    /api/nodes/{node_id}/pods/{name}       → Schema__Pod__Info (404 on miss)
#   GET    /api/nodes/{node_id}/pods/{name}/stats → Schema__Pod__Stats (404 on miss)
#   GET    /api/nodes/{node_id}/pods/{name}/logs  → Schema__Pod__Logs__Response
#   POST   /api/nodes/{node_id}/pods/{name}/stop  → Schema__Pod__Stop__Response
#   DELETE /api/nodes/{node_id}/pods/{name}       → Schema__Pod__Stop__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                   import HTTPException
from osbot_fast_api.api.routes.Fast_API__Routes                               import Fast_API__Routes

from sg_compute.core.pod.Pod__Manager                                         import Pod__Manager
from sg_compute.core.pod.schemas.Schema__Pod__Start__Request                  import Schema__Pod__Start__Request
from sg_compute.primitives.Safe_Str__Node__Id                                 import Safe_Str__Node__Id
from sg_compute.primitives.Safe_Str__Pod__Name                                import Safe_Str__Pod__Name

TAG__ROUTES_COMPUTE_PODS = 'pods'


class Routes__Compute__Pods(Fast_API__Routes):
    tag     : str         = TAG__ROUTES_COMPUTE_PODS
    prefix  : str         = '/api/nodes'
    manager : Pod__Manager

    def _sidecar_error(self, node_id: str, e: Exception) -> None:
        raise HTTPException(status_code=503,
                            detail=f'sidecar unreachable for node {node_id}: {e}')

    def list_pods(self, node_id: str) -> dict:                               # GET /{node_id}/pods/list
        try:
            return self.manager.list_pods(Safe_Str__Node__Id(node_id)).json()
        except Exception as e:
            self._sidecar_error(node_id, e)
    list_pods.__route_path__ = '/{node_id}/pods/list'

    def start_pod(self, node_id: str, body: Schema__Pod__Start__Request) -> dict:  # POST /{node_id}/pods
        try:
            return self.manager.start_pod(Safe_Str__Node__Id(node_id), body).json()
        except Exception as e:
            self._sidecar_error(node_id, e)
    start_pod.__route_path__ = '/{node_id}/pods'

    def get_pod(self, node_id: str, name: str) -> dict:                      # GET /{node_id}/pods/{name}
        try:
            pod = self.manager.get_pod(Safe_Str__Node__Id(node_id), Safe_Str__Pod__Name(name))
        except Exception as e:
            self._sidecar_error(node_id, e)
        if pod is None:
            raise HTTPException(status_code=404, detail=f'pod {name!r} not found on node {node_id!r}')
        return pod.json()
    get_pod.__route_path__ = '/{node_id}/pods/{name}'

    def get_pod_stats(self, node_id: str, name: str) -> dict:                 # GET /{node_id}/pods/{name}/stats
        try:
            stats = self.manager.get_pod_stats(Safe_Str__Node__Id(node_id), Safe_Str__Pod__Name(name))
        except Exception as e:
            self._sidecar_error(node_id, e)
        if stats is None:
            raise HTTPException(status_code=404, detail=f'stats for pod {name!r} not found on node {node_id!r}')
        return stats.json()
    get_pod_stats.__route_path__ = '/{node_id}/pods/{name}/stats'

    def get_pod_logs(self, node_id: str, name: str,                          # GET /{node_id}/pods/{name}/logs
                     tail: int = 100, timestamps: bool = False) -> dict:
        try:
            return self.manager.get_pod_logs(Safe_Str__Node__Id(node_id), Safe_Str__Pod__Name(name),
                                             tail=tail, timestamps=timestamps).json()
        except Exception as e:
            self._sidecar_error(node_id, e)
    get_pod_logs.__route_path__ = '/{node_id}/pods/{name}/logs'

    def stop_pod(self, node_id: str, name: str) -> dict:                     # POST /{node_id}/pods/{name}/stop
        try:
            return self.manager.stop_pod(Safe_Str__Node__Id(node_id), Safe_Str__Pod__Name(name)).json()
        except Exception as e:
            self._sidecar_error(node_id, e)
    stop_pod.__route_path__ = '/{node_id}/pods/{name}/stop'

    def remove_pod(self, node_id: str, name: str) -> dict:                   # DELETE /{node_id}/pods/{name}
        try:
            return self.manager.remove_pod(Safe_Str__Node__Id(node_id), Safe_Str__Pod__Name(name)).json()
        except Exception as e:
            self._sidecar_error(node_id, e)
    remove_pod.__route_path__ = '/{node_id}/pods/{name}'

    def setup_routes(self):
        self.add_route_get   (self.list_pods    )
        self.add_route_post  (self.start_pod    )
        self.add_route_get   (self.get_pod      )
        self.add_route_get   (self.get_pod_stats)
        self.add_route_get   (self.get_pod_logs )
        self.add_route_post  (self.stop_pod    )
        self.add_route_delete(self.remove_pod  )
