# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__Vault__Folder_Ref
# The (Transfer-ID, read key) pair a slug deterministically derives to. Used by
# Vault__Fetcher to fetch the immutable vault folder from SG/API.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Safe_Str__Read_Key              import Safe_Str__Read_Key
from vault_publish.schemas.Safe_Str__Transfer_Id           import Safe_Str__Transfer_Id


class Schema__Vault__Folder_Ref(Type_Safe):
    transfer_id : Safe_Str__Transfer_Id                    # SG/API transfer identifier
    read_key    : Safe_Str__Read_Key                       # SG/API read key — stays inside the resolution layer
