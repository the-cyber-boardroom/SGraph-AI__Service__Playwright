# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__List__Response
# Returned by GET /vault-publish/list.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.List__Slug                      import List__Slug


class Schema__VaultPublish__List__Response(Type_Safe):
    slugs : List__Slug                                    # registered slugs
