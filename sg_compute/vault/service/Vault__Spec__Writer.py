# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Vault__Spec__Writer
# Validates a vault-write request and produces a receipt. Actual vault
# persistence is stubbed — replaced when vault I/O lands (BV2.x follow-on).
#
# write_handles_by_spec: spec_id → set[str] of allowed handle slugs.
#   Empty set (default) = no restriction on handles.
#   spec_registry: when supplied, spec_id is validated against the registry.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
from datetime                                                                import datetime, timezone
from typing                                                                  import Optional

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe

from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry
from sg_compute.vault.collections.List__Schema__Vault__Write__Receipt        import List__Schema__Vault__Write__Receipt
from sg_compute.vault.enums.Enum__Vault__Error_Code                          import Enum__Vault__Error_Code
from sg_compute.vault.primitives.Safe_Int__Bytes                             import Safe_Int__Bytes
from sg_compute.vault.primitives.Safe_Str__ISO_Datetime                      import Safe_Str__ISO_Datetime
from sg_compute.vault.primitives.Safe_Str__Spec__Type_Id                     import Safe_Str__Spec__Type_Id
from sg_compute.vault.primitives.Safe_Str__SHA256                            import Safe_Str__SHA256
from sg_compute.vault.primitives.Safe_Str__Stack__Id                         import Safe_Str__Stack__Id
from sg_compute.vault.primitives.Safe_Str__Vault__Handle                     import Safe_Str__Vault__Handle
from sg_compute.vault.primitives.Safe_Str__Vault__Path                       import Safe_Str__Vault__Path
from sg_compute.vault.schemas.Schema__Vault__Write__Receipt                  import Schema__Vault__Write__Receipt

MAX_BLOB_BYTES   = 10 * 1024 * 1024                                          # 10 MB hard cap
SHARED_STACK_ID  = '_shared'                                                 # sentinel for spec-wide (cross-node) blobs


class Vault__Spec__Writer(Type_Safe):
    spec_registry       : Optional[Spec__Registry] = None                   # when set, spec_id is validated
    write_handles_by_spec : dict                                             # spec_id → set/list of allowed handles; empty = unrestricted
    vault_attached      : bool = False                                       # True when a vault token is wired up

    # ── validation ───────────────────────────────────────────────────────────

    def _validate_spec_id(self, spec_id: str) -> Optional[str]:             # None = valid; str = error code
        if self.spec_registry is not None:
            if self.spec_registry.get(spec_id) is None:
                return Enum__Vault__Error_Code.UNKNOWN_SPEC
        elif self.write_handles_by_spec:                                     # no registry: validate against handles dict
            if spec_id not in self.write_handles_by_spec:
                return Enum__Vault__Error_Code.UNKNOWN_SPEC
        return None

    def _validate_handle(self, spec_id: str, handle: str) -> Optional[str]:
        allowed = set(self.write_handles_by_spec.get(spec_id, []))
        if allowed and handle not in allowed:                                # empty = no restriction
            return Enum__Vault__Error_Code.DISALLOWED_HANDLE
        return None

    def _validate_size(self, body: bytes) -> Optional[str]:
        if len(body) > MAX_BLOB_BYTES:
            return Enum__Vault__Error_Code.PAYLOAD_TOO_LARGE
        return None

    # ── public API ────────────────────────────────────────────────────────────

    def write(self, spec_id: str, stack_id: str, handle: str,
              body: bytes) -> tuple:
        if not self.vault_attached:
            return None, Enum__Vault__Error_Code.NO_VAULT_ATTACHED
        err = self._validate_spec_id(spec_id)
        if err:
            return None, err
        err = self._validate_handle(spec_id, handle)
        if err:
            return None, err
        err = self._validate_size(body)
        if err:
            return None, err
        vault_path = f'spec/{spec_id}/{stack_id}/{handle}'
        sha256     = hashlib.sha256(body).hexdigest()
        written_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        receipt = Schema__Vault__Write__Receipt(
            spec_id       = Safe_Str__Spec__Type_Id(spec_id)   ,
            stack_id      = Safe_Str__Stack__Id(stack_id)      ,
            handle        = Safe_Str__Vault__Handle(handle)    ,
            bytes_written = Safe_Int__Bytes(len(body))         ,
            sha256        = Safe_Str__SHA256(sha256)           ,
            written_at    = Safe_Str__ISO_Datetime(written_at) ,
            vault_path    = Safe_Str__Vault__Path(vault_path)  ,
        )
        return receipt, None

    def get_metadata(self, spec_id: str, stack_id: str,
                     handle: str) -> tuple:
        if not self.vault_attached:
            return None, Enum__Vault__Error_Code.NO_VAULT_ATTACHED
        err = self._validate_spec_id(spec_id)
        if err:
            return None, err
        return None, None                                                    # stub: real lookup in follow-on

    def list_spec(self, spec_id: str) -> tuple:
        if not self.vault_attached:
            return None, Enum__Vault__Error_Code.NO_VAULT_ATTACHED
        err = self._validate_spec_id(spec_id)
        if err:
            return None, err
        return List__Schema__Vault__Write__Receipt(), None                   # stub: real vault scan in follow-on

    def delete(self, spec_id: str, stack_id: str,
               handle: str) -> tuple:
        if not self.vault_attached:
            return False, Enum__Vault__Error_Code.NO_VAULT_ATTACHED
        err = self._validate_spec_id(spec_id)
        if err:
            return False, err
        err = self._validate_handle(spec_id, handle)
        if err:
            return False, err
        return True, None                                                    # stub: real vault delete in follow-on
