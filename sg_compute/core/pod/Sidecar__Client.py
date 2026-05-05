# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Sidecar__Client
# HTTP client for one Node's sidecar (Fast_API__Host__Control on :19009).
# Instantiated by Pod__Manager per-call; overridden in tests by subclass.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe


class Sidecar__Client(Type_Safe):
    host_api_url : str = ''
    api_key      : str = ''

    def _headers(self) -> dict:
        return {'X-API-Key': self.api_key}

    def _get(self, path: str) -> dict:
        import requests
        r = requests.get(f'{self.host_api_url}{path}', headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict = None) -> dict:
        import requests
        r = requests.post(f'{self.host_api_url}{path}', headers=self._headers(),
                          json=body or {}, timeout=10)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> dict:
        import requests
        r = requests.delete(f'{self.host_api_url}{path}', headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def list_pods(self) -> list:
        return self._get('/pods/list').get('pods', [])

    def get_pod(self, name: str) -> dict | None:
        try:
            return self._get(f'/pods/{name}')
        except Exception:
            return None

    def get_pod_logs(self, name: str, tail: int = 100, timestamps: bool = False) -> dict | None:
        try:
            return self._get(f'/pods/{name}/logs?tail={tail}&timestamps={str(timestamps).lower()}')
        except Exception:
            return None

    def get_pod_stats(self, name: str) -> dict | None:
        try:
            return self._get(f'/pods/{name}/stats')
        except Exception:
            return None

    def start_pod(self, body: dict) -> dict:
        return self._post('/pods', body)

    def stop_pod(self, name: str) -> dict:
        return self._post(f'/pods/{name}/stop')

    def remove_pod(self, name: str) -> dict:
        return self._delete(f'/pods/{name}')
