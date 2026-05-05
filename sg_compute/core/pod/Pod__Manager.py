# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Pod__Manager
# Control-plane bridge to each Node's sidecar for pod operations.
# Resolves node → public_ip → sidecar URL, then delegates to Sidecar__Client.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.pod.Sidecar__Client                                     import Sidecar__Client
from sg_compute.core.pod.schemas.Schema__Pod__Info                           import Schema__Pod__Info
from sg_compute.core.pod.schemas.Schema__Pod__List                           import Schema__Pod__List
from sg_compute.core.pod.schemas.Schema__Pod__Logs__Response                 import Schema__Pod__Logs__Response
from sg_compute.core.pod.schemas.Schema__Pod__Start__Request                 import Schema__Pod__Start__Request
from sg_compute.core.pod.schemas.Schema__Pod__Stats                          import Schema__Pod__Stats
from sg_compute.core.pod.schemas.Schema__Pod__Stop__Response                 import Schema__Pod__Stop__Response
from sg_compute.platforms.Platform                                            import Platform
from sg_compute.primitives.enums.Enum__Pod__State                            import Enum__Pod__State
from sg_compute.primitives.Safe_Int__Log__Lines                              import Safe_Int__Log__Lines
from sg_compute.primitives.Safe_Int__Pids                                    import Safe_Int__Pids
from sg_compute.primitives.Safe_Str__Docker__Image                           import Safe_Str__Docker__Image
from sg_compute.primitives.Safe_Str__Log__Content                            import Safe_Str__Log__Content
from sg_compute.primitives.Safe_Str__Message                                 import Safe_Str__Message
from sg_compute.primitives.Safe_Str__Node__Id                                import Safe_Str__Node__Id
from sg_compute.primitives.Safe_Str__Pod__Name                               import Safe_Str__Pod__Name

SIDECAR_PORT        = 19009
SIDECAR_API_KEY_ENV = 'SG_COMPUTE__SIDECAR__API_KEY'  # local-dev fallback only; per-node SSM key takes priority in production


class Pod__Manager(Type_Safe):
    platform : Platform

    def _sidecar_client(self, node_id: str) -> Sidecar__Client | None:
        node = self.platform.get_node(node_id)
        if node is None or not node.public_ip:
            return None
        api_key = self._resolve_api_key(node_id, node.host_api_key_ssm_path)
        return Sidecar__Client(host_api_url=f'http://{node.public_ip}:{SIDECAR_PORT}',
                               api_key=api_key)

    def _resolve_api_key(self, node_id: str, ssm_path: str) -> str:           # per-node SSM key; env var is local-dev fallback only
        if ssm_path:
            from sg_compute.platforms.ec2.secrets.SSM__Sidecar__Key import SSM__Sidecar__Key
            key = SSM__Sidecar__Key().read(node_id)
            if key:
                return key
        return os.environ.get(SIDECAR_API_KEY_ENV, '')                         # local dev / CI only — not production-safe

    @staticmethod
    def _map_pod_info(raw: dict, node_id: str) -> Schema__Pod__Info:
        state_map = {'running': Enum__Pod__State.RUNNING,
                     'created': Enum__Pod__State.PENDING ,
                     'exited' : Enum__Pod__State.STOPPED ,
                     'paused' : Enum__Pod__State.STOPPED }
        raw_status = raw.get('status', raw.get('state', ''))
        return Schema__Pod__Info(pod_name = Safe_Str__Pod__Name   (raw.get('name' , '')),
                                 node_id  = Safe_Str__Node__Id    (node_id             ),
                                 image    = Safe_Str__Docker__Image(raw.get('image', '')),
                                 state    = state_map.get(raw_status, Enum__Pod__State.FAILED),
                                 ports    = Safe_Str__Message      (str(raw.get('ports', ''))))

    def list_pods(self, node_id: Safe_Str__Node__Id) -> Schema__Pod__List:
        client = self._sidecar_client(node_id)
        if client is None:
            return Schema__Pod__List(pods=[])
        raw_pods = client.list_pods()
        pods = [self._map_pod_info(p, node_id) for p in raw_pods]
        return Schema__Pod__List(pods=pods)

    def start_pod(self, node_id: Safe_Str__Node__Id, request: Schema__Pod__Start__Request) -> Schema__Pod__Info:
        client = self._sidecar_client(node_id)
        if client is None:
            return Schema__Pod__Info(node_id=node_id)
        raw = client.start_pod(request.json())
        return self._map_pod_info(raw, node_id)

    def get_pod(self, node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name) -> Schema__Pod__Info | None:
        client = self._sidecar_client(node_id)
        if client is None:
            return None
        raw = client.get_pod(pod_name)
        return self._map_pod_info(raw, node_id) if raw else None

    def get_pod_stats(self, node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name) -> Schema__Pod__Stats | None:
        client = self._sidecar_client(node_id)
        if client is None:
            return None
        raw = client.get_pod_stats(pod_name)
        if raw is None:
            return None
        return Schema__Pod__Stats(container      = Safe_Str__Pod__Name(raw.get('container'     , pod_name)),
                                  cpu_percent    = raw.get('cpu_percent'   , 0.0)                         ,
                                  mem_usage_mb   = raw.get('mem_usage_mb'  , 0.0)                         ,
                                  mem_limit_mb   = raw.get('mem_limit_mb'  , 0.0)                         ,
                                  mem_percent    = raw.get('mem_percent'   , 0.0)                         ,
                                  net_rx_mb      = raw.get('net_rx_mb'     , 0.0)                         ,
                                  net_tx_mb      = raw.get('net_tx_mb'     , 0.0)                         ,
                                  block_read_mb  = raw.get('block_read_mb' , 0.0)                         ,
                                  block_write_mb = raw.get('block_write_mb', 0.0)                         ,
                                  pids           = Safe_Int__Pids(raw.get('pids', 0))                     )

    def get_pod_logs(self, node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name,
                     tail: int = 100, timestamps: bool = False) -> Schema__Pod__Logs__Response:
        client = self._sidecar_client(node_id)
        if client is None:
            return Schema__Pod__Logs__Response()
        raw = client.get_pod_logs(pod_name, tail=tail, timestamps=timestamps) or {}
        return Schema__Pod__Logs__Response(container = Safe_Str__Pod__Name   (raw.get('container', pod_name)),
                                           lines     = Safe_Int__Log__Lines  (raw.get('lines'    , 0))       ,
                                           content   = Safe_Str__Log__Content(raw.get('content'  , ''))      ,
                                           truncated = raw.get('truncated', False)                            )

    def stop_pod(self, node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name) -> Schema__Pod__Stop__Response:
        client = self._sidecar_client(node_id)
        if client is None:
            return Schema__Pod__Stop__Response()
        raw = client.stop_pod(pod_name) or {}
        return Schema__Pod__Stop__Response(name    = Safe_Str__Pod__Name(raw.get('name' , pod_name)),
                                           stopped = raw.get('stopped', False)                       ,
                                           removed = raw.get('removed', False)                       ,
                                           error   = Safe_Str__Message(raw.get('error' , ''))        )

    def remove_pod(self, node_id: Safe_Str__Node__Id, pod_name: Safe_Str__Pod__Name) -> Schema__Pod__Stop__Response:
        client = self._sidecar_client(node_id)
        if client is None:
            return Schema__Pod__Stop__Response()
        raw = client.remove_pod(pod_name) or {}
        return Schema__Pod__Stop__Response(name    = Safe_Str__Pod__Name(raw.get('name' , pod_name)),
                                           stopped = raw.get('stopped', False)                       ,
                                           removed = raw.get('removed', False)                       ,
                                           error   = Safe_Str__Message(raw.get('error' , ''))        )
