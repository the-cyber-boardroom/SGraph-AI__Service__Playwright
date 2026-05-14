# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Host_Plane__Client
# Thin typed HTTP client over the host-plane pods API
# (sg_compute.host_plane.fast_api.Fast_API__Host__Control). The playwright
# stack service drives pod lifecycle through this client rather than shelling
# out to docker — keeps the orchestration reusable on podman / k8s / Fargate.
#
# Methods return plain dicts / lists straight from the host-plane; the service
# does the Type_Safe schema mapping. This keeps the client trivially fakeable
# by subclassing (no mocks) for unit tests.
#
# Host-plane endpoints used (tag 'pods'):
#   GET    /pods/list        → list of pod dicts
#   POST   /pods             → Schema__Pod__Start__Response dict
#   GET    /pods/{name}      → Schema__Pod__Info dict   (404 → None)
#   DELETE /pods/{name}      → Schema__Pod__Stop__Response dict
# ═══════════════════════════════════════════════════════════════════════════════

import requests

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


DEFAULT_API_KEY_HEADER = 'x-api-key'                                                # Serverless__Fast_API default; override via api_key_header
HTTP_TIMEOUT_SECONDS   = 30


class Host_Plane__Client(Type_Safe):
    base_url       : str                                                            # host-plane base URL, e.g. http://10.0.1.4:19009
    api_key        : str                                                            # host-plane API key
    api_key_header : str = DEFAULT_API_KEY_HEADER

    def headers(self) -> dict:
        return {self.api_key_header: self.api_key} if self.api_key else {}

    def url(self, path: str) -> str:                                                # path is appended under /pods
        return f'{str(self.base_url).rstrip("/")}/pods{path}'

    def start_pod(self, name: str, image: str, ports: dict,                         # POST /pods
                  env: dict, type_id: str) -> dict:
        body = {'name': name, 'image': image, 'ports': ports,
                'env': env, 'type_id': type_id}
        response = requests.post(self.url(''), json=body,
                                 headers=self.headers(), timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()

    def list_pods(self) -> list:                                                    # GET /pods/list
        response = requests.get(self.url('/list'), headers=self.headers(),
                                timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):                                                  # Schema__Pod__List wrapper — pull the pods field
            return data.get('pods', [])
        return data                                                                 # already a list

    def get_pod(self, name: str) -> dict:                                           # GET /pods/{name} — None on 404
        response = requests.get(self.url(f'/{name}'), headers=self.headers(),
                                timeout=HTTP_TIMEOUT_SECONDS)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def remove_pod(self, name: str) -> dict:                                        # DELETE /pods/{name}
        response = requests.delete(self.url(f'/{name}'), headers=self.headers(),
                                   timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
