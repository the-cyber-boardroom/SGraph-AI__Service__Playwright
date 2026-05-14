# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vault_App__HTTP__Probe
# Reachability probes for the vault-app stack. Checks sg-send-vault and
# the playwright service health endpoints. Pure logic; no print().
# ═══════════════════════════════════════════════════════════════════════════════

import requests

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.vault_app.enums.Enum__Vault_App__Stack__State  import Enum__Vault_App__Stack__State
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Health    import Schema__Vault_App__Health
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Info import Schema__Vault_App__Stack__Info

PROBE_TIMEOUT = 5


class Vault_App__HTTP__Probe(Type_Safe):

    def check(self, info: Schema__Vault_App__Stack__Info) -> Schema__Vault_App__Health:
        vault_ok      = self._get_ok(f'{info.vault_url}info/health')
        playwright_ok = self._get_ok(f'http://{info.public_ip}:8000/health/status')
        state         = (Enum__Vault_App__Stack__State.READY
                         if vault_ok
                         else Enum__Vault_App__Stack__State.RUNNING)
        return Schema__Vault_App__Health(
            stack_name    = info.stack_name ,
            state         = state           ,
            vault_ok      = vault_ok        ,
            playwright_ok = playwright_ok   ,
        )

    def _get_ok(self, url: str) -> bool:
        try:
            return requests.get(url, timeout=PROBE_TIMEOUT).status_code == 200
        except Exception:
            return False
