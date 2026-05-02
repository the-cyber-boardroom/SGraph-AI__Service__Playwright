# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Routes__Vault__Plugin
# Per-plugin vault write/read/list/delete contract.
#
# Endpoints
# ─────────
#   PUT    /vault/plugin/{plugin_id}/{stack_id}/{handle}          → Schema__Vault__Write__Receipt
#   GET    /vault/plugin/{plugin_id}/{stack_id}/{handle}/metadata → Schema__Vault__Write__Receipt
#   GET    /vault/plugin/{plugin_id}                              → list of receipts
#   DELETE /vault/plugin/{plugin_id}/{stack_id}/{handle}          → 204
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                            import Body, HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                                        import Fast_API__Routes

from sgraph_ai_service_playwright__cli.vault.enums.Enum__Vault__Error_Code              import Enum__Vault__Error_Code
from sgraph_ai_service_playwright__cli.vault.service.Vault__Plugin__Writer              import Vault__Plugin__Writer

_STATUS_FOR_ERROR = {
    Enum__Vault__Error_Code.NO_VAULT_ATTACHED : 409,
    Enum__Vault__Error_Code.UNKNOWN_PLUGIN    : 400,
    Enum__Vault__Error_Code.DISALLOWED_HANDLE : 400,
    Enum__Vault__Error_Code.PAYLOAD_TOO_LARGE : 413,
}


def _raise(error_code: Enum__Vault__Error_Code):
    status = _STATUS_FOR_ERROR.get(error_code, 400)
    raise HTTPException(status_code=status, detail={'error_code': error_code.value})


class Routes__Vault__Plugin(Fast_API__Routes):
    tag     : str                  = 'vault'
    service : Vault__Plugin__Writer

    def write(self, plugin_id: str, stack_id: str, handle: str,
              body: bytes = Body(...)) -> dict:
        receipt, err = self.service.write(plugin_id, stack_id, handle, body)
        if err:
            _raise(err)
        return receipt.json()
    write.__route_path__ = '/plugin/{plugin_id}/{stack_id}/{handle}'

    def metadata(self, plugin_id: str, stack_id: str, handle: str) -> dict:
        receipt, err = self.service.get_metadata(plugin_id, stack_id, handle)
        if err:
            _raise(err)
        if receipt is None:
            raise HTTPException(status_code=404, detail='not found')
        return receipt.json()
    metadata.__route_path__ = '/plugin/{plugin_id}/{stack_id}/{handle}/metadata'

    def list_plugin(self, plugin_id: str) -> dict:
        receipts, err = self.service.list_plugin(plugin_id)
        if err:
            _raise(err)
        return {'plugin_id': plugin_id, 'receipts': [r.json() for r in receipts]}
    list_plugin.__route_path__ = '/plugin/{plugin_id}'

    def delete(self, plugin_id: str, stack_id: str, handle: str) -> dict:
        ok, err = self.service.delete(plugin_id, stack_id, handle)
        if err:
            _raise(err)
        return {}
    delete.__route_path__ = '/plugin/{plugin_id}/{stack_id}/{handle}'

    def setup_routes(self):
        self.add_route_put   (self.write      )
        self.add_route_get   (self.metadata   )
        self.add_route_get   (self.list_plugin)
        self.add_route_delete(self.delete     )
