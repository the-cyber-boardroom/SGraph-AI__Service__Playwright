# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Vault__Write__Receipt
# Returned by PUT /api/vault/spec/{spec_id}/{stack_id}/{handle}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe

from sg_compute.vault.primitives.Safe_Int__Bytes                             import Safe_Int__Bytes
from sg_compute.vault.primitives.Safe_Str__ISO_Datetime                      import Safe_Str__ISO_Datetime
from sg_compute.vault.primitives.Safe_Str__Spec__Type_Id                     import Safe_Str__Spec__Type_Id
from sg_compute.vault.primitives.Safe_Str__SHA256                            import Safe_Str__SHA256
from sg_compute.vault.primitives.Safe_Str__Stack__Id                         import Safe_Str__Stack__Id
from sg_compute.vault.primitives.Safe_Str__Vault__Handle                     import Safe_Str__Vault__Handle
from sg_compute.vault.primitives.Safe_Str__Vault__Path                       import Safe_Str__Vault__Path


class Schema__Vault__Write__Receipt(Type_Safe):
    spec_id       : Safe_Str__Spec__Type_Id                  # e.g. 'firefox'
    stack_id      : Safe_Str__Stack__Id                      # node stack-id or '_shared'
    handle        : Safe_Str__Vault__Handle                  # e.g. 'credentials'
    bytes_written : Safe_Int__Bytes                          # raw byte count of the written blob
    sha256        : Safe_Str__SHA256                         # hex digest — detect duplicate uploads
    written_at    : Safe_Str__ISO_Datetime                   # ISO 8601 UTC timestamp
    vault_path    : Safe_Str__Vault__Path                    # spec/{spec_id}/{stack_id}/{handle}
