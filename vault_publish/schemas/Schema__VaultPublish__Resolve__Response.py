# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__Resolve__Response
# Returned by POST /vault-publish/resolve. Shows the deterministic derivation
# and a manifest summary. No side effects ran.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Enum__Vault_App__Runtime        import Enum__Vault_App__Runtime
from vault_publish.schemas.Enum__Vault_App__Type           import Enum__Vault_App__Type
from vault_publish.schemas.Safe_Str__Read_Key              import Safe_Str__Read_Key
from vault_publish.schemas.Safe_Str__Slug                  import Safe_Str__Slug
from vault_publish.schemas.Safe_Str__Transfer_Id           import Safe_Str__Transfer_Id


class Schema__VaultPublish__Resolve__Response(Type_Safe):
    slug         : Safe_Str__Slug                         # the slug resolved
    transfer_id  : Safe_Str__Transfer_Id                  # derived SG/API transfer id
    read_key     : Safe_Str__Read_Key                     # derived SG/API read key
    app_type     : Enum__Vault_App__Type                  # manifest summary — app kind
    runtime      : Enum__Vault_App__Runtime               # manifest summary — runtime
