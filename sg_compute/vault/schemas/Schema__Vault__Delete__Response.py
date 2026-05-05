# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Vault__Delete__Response
# Returned by DELETE /api/vault/spec/{spec_id}/{stack_id}/{handle}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe

from sg_compute.vault.primitives.Safe_Str__Spec__Type_Id                     import Safe_Str__Spec__Type_Id
from sg_compute.vault.primitives.Safe_Str__Stack__Id                         import Safe_Str__Stack__Id
from sg_compute.vault.primitives.Safe_Str__Vault__Handle                     import Safe_Str__Vault__Handle
from sg_compute.vault.primitives.Safe_Str__Vault__Path                       import Safe_Str__Vault__Path


class Schema__Vault__Delete__Response(Type_Safe):
    spec_id    : Safe_Str__Spec__Type_Id
    stack_id   : Safe_Str__Stack__Id
    handle     : Safe_Str__Vault__Handle
    vault_path : Safe_Str__Vault__Path
    deleted    : bool = False
