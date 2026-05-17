# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__Unpublish__Response
# Returned by DELETE /vault-publish/unpublish/{slug}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Safe_Str__Slug                  import Safe_Str__Slug


class Schema__VaultPublish__Unpublish__Response(Type_Safe):
    slug        : Safe_Str__Slug                          # the slug acted on
    unpublished : bool                                    # True if an association was removed
