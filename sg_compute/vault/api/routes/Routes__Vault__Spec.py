# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Routes__Vault__Spec
# Per-spec vault write/read/list/delete.
#
# Endpoints (mounted at /api/vault):
#   PUT    /spec/{spec_id}/{stack_id}/{handle}          → Schema__Vault__Write__Receipt
#   GET    /spec/{spec_id}/{stack_id}/{handle}/metadata → Schema__Vault__Write__Receipt
#   GET    /spec/{spec_id}                              → Schema__Vault__List__Response
#   DELETE /spec/{spec_id}/{stack_id}/{handle}          → Schema__Vault__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi                                                                 import Body, HTTPException

from osbot_fast_api.api.routes.Fast_API__Routes                              import Fast_API__Routes

from sg_compute.vault.enums.Enum__Vault__Error_Code                          import Enum__Vault__Error_Code
from sg_compute.vault.primitives.Safe_Str__Spec__Type_Id                     import Safe_Str__Spec__Type_Id
from sg_compute.vault.primitives.Safe_Str__Stack__Id                         import Safe_Str__Stack__Id
from sg_compute.vault.primitives.Safe_Str__Vault__Handle                     import Safe_Str__Vault__Handle
from sg_compute.vault.primitives.Safe_Str__Vault__Path                       import Safe_Str__Vault__Path
from sg_compute.vault.schemas.Schema__Vault__Delete__Response                import Schema__Vault__Delete__Response
from sg_compute.vault.schemas.Schema__Vault__List__Response                  import Schema__Vault__List__Response
from sg_compute.vault.service.Vault__Spec__Writer                            import Vault__Spec__Writer

_STATUS_FOR_ERROR = {
    Enum__Vault__Error_Code.NO_VAULT_ATTACHED : 409,
    Enum__Vault__Error_Code.UNKNOWN_SPEC      : 400,
    Enum__Vault__Error_Code.DISALLOWED_HANDLE : 400,
    Enum__Vault__Error_Code.PAYLOAD_TOO_LARGE : 413,
}


def _raise(error_code: Enum__Vault__Error_Code):
    status = _STATUS_FOR_ERROR.get(error_code, 400)
    raise HTTPException(status_code=status, detail={'error_code': error_code.value})


class Routes__Vault__Spec(Fast_API__Routes):
    tag     : str               = 'vault'
    service : Vault__Spec__Writer

    def write(self, spec_id: str, stack_id: str, handle: str,
              body: bytes = Body(...)) -> dict:
        receipt, err = self.service.write(spec_id, stack_id, handle, body)
        if err:
            _raise(err)
        return receipt.json()
    write.__route_path__ = '/spec/{spec_id}/{stack_id}/{handle}'

    def metadata(self, spec_id: str, stack_id: str, handle: str) -> dict:
        receipt, err = self.service.get_metadata(spec_id, stack_id, handle)
        if err:
            _raise(err)
        if receipt is None:
            raise HTTPException(status_code=404, detail='not found')
        return receipt.json()
    metadata.__route_path__ = '/spec/{spec_id}/{stack_id}/{handle}/metadata'

    def list_spec(self, spec_id: str) -> dict:
        receipts, err = self.service.list_spec(spec_id)
        if err:
            _raise(err)
        return Schema__Vault__List__Response(
            spec_id  = Safe_Str__Spec__Type_Id(spec_id),
            receipts = receipts,
        ).json()
    list_spec.__route_path__ = '/spec/{spec_id}'

    def delete(self, spec_id: str, stack_id: str, handle: str) -> dict:
        ok, err = self.service.delete(spec_id, stack_id, handle)
        if err:
            _raise(err)
        vault_path = f'spec/{spec_id}/{stack_id}/{handle}'
        return Schema__Vault__Delete__Response(
            spec_id    = Safe_Str__Spec__Type_Id(spec_id)    ,
            stack_id   = Safe_Str__Stack__Id(stack_id)       ,
            handle     = Safe_Str__Vault__Handle(handle)     ,
            vault_path = Safe_Str__Vault__Path(vault_path)   ,
            deleted    = ok                                   ,
        ).json()
    delete.__route_path__ = '/spec/{spec_id}/{stack_id}/{handle}'

    def setup_routes(self):
        self.add_route_put   (self.write    )
        self.add_route_get   (self.metadata )
        self.add_route_get   (self.list_spec)
        self.add_route_delete(self.delete   )
