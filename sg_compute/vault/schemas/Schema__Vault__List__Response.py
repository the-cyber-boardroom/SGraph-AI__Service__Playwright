# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Vault__List__Response
# Returned by GET /api/vault/spec/{spec_id}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                         import Type_Safe

from sg_compute.vault.collections.List__Schema__Vault__Write__Receipt        import List__Schema__Vault__Write__Receipt
from sg_compute.vault.primitives.Safe_Str__Spec__Type_Id                     import Safe_Str__Spec__Type_Id


class Schema__Vault__List__Response(Type_Safe):
    spec_id  : Safe_Str__Spec__Type_Id
    receipts : List__Schema__Vault__Write__Receipt
