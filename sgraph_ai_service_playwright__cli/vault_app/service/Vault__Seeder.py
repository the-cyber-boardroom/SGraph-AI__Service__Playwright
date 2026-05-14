# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vault__Seeder
# Clones one or more vault keys into a running sg-send-vault instance by
# invoking `sgit clone` via the host-plane /shell endpoint. Idempotent —
# skips keys whose vault already exists at the target endpoint.
#
# Dependency: host-plane must expose POST /shell/execute (Routes__Host__Shell).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url            import Safe_Str__Url


class Vault__Seeder(Type_Safe):
    vault_endpoint   : Safe_Str__Url                                                # e.g. http://<ip>:8080
    vault_token      : Safe_Str__Text                                               # SGRAPH_SEND__ACCESS_TOKEN value
    host_plane_url   : Safe_Str__Url                                                # e.g. http://localhost:<host_plane_port>
    host_plane_token : Safe_Str__Text                                               # FAST_API__AUTH__API_KEY__VALUE value

    def seed(self, vault_key: str) -> bool:                                         # returns True on clone, False if already present
        if self._vault_exists(vault_key):
            return False
        self._clone(vault_key)
        return True

    def seed_all(self, keys_csv: str) -> dict:                                      # keys_csv: comma-separated vault keys; returns {key: seeded}
        results = {}
        for key in (k.strip() for k in keys_csv.split(',') if k.strip()):
            results[key] = self.seed(key)
        return results

    def _vault_exists(self, vault_key: str) -> bool:                               # HEAD /api/vault/read/{vault_key}/ via requests
        import requests
        try:
            headers = {'x-sgraph-access-token': str(self.vault_token)} if self.vault_token else {}
            resp = requests.head(f'{self.vault_endpoint}/api/vault/read/{vault_key}/',
                                 headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def _clone(self, vault_key: str) -> None:                                       # POST /shell/execute on host-plane
        import requests
        headers  = {str(self.host_plane_token) if self.host_plane_token else 'X-API-Key': str(self.host_plane_token)}
        cmd      = ['sgit', 'clone', vault_key,
                    '--endpoint', str(self.vault_endpoint),
                    '--token',    str(self.vault_token)]
        payload  = {'command': cmd}
        requests.post(f'{self.host_plane_url}/shell/execute',
                      json=payload, headers=headers, timeout=60)
