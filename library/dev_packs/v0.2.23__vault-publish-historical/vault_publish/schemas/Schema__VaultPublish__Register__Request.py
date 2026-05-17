# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__Register__Request
# Body for POST /vault-publish/register. The slug is carried as a raw-ish string
# so Slug__Validator can return a clear, specific error rather than failing at
# parse time.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Safe_Str__Message               import Safe_Str__Message
from vault_publish.schemas.Safe_Str__Owner_Id              import Safe_Str__Owner_Id
from vault_publish.schemas.Safe_Str__Signing_Key_Ref       import Safe_Str__Signing_Key_Ref


class Schema__VaultPublish__Register__Request(Type_Safe):
    slug                   : Safe_Str__Message            # candidate slug — validated by Slug__Validator
    owner_id               : Safe_Str__Owner_Id           # owner the slug is bound to
    signing_public_key_ref : Safe_Str__Signing_Key_Ref    # key that will verify the manifest
