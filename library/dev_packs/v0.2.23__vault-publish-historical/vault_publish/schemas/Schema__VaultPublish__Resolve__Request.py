# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__Resolve__Request
# Body for POST /vault-publish/resolve — derive the vault folder ref and
# summarise the manifest, with no side effects. Operator / debug aid.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Safe_Str__Message               import Safe_Str__Message


class Schema__VaultPublish__Resolve__Request(Type_Safe):
    slug : Safe_Str__Message                              # candidate slug — validated by Slug__Validator
