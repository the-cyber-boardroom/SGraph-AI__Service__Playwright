# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__Register__Response
# Returned by POST /vault-publish/register on success.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Safe_Str__Message               import Safe_Str__Message
from vault_publish.schemas.Safe_Str__Owner_Id              import Safe_Str__Owner_Id
from vault_publish.schemas.Safe_Str__Slug                  import Safe_Str__Slug


class Schema__VaultPublish__Register__Response(Type_Safe):
    slug       : Safe_Str__Slug                           # the registered slug
    owner_id   : Safe_Str__Owner_Id                       # owner it is bound to
    url        : Safe_Str__Message                        # the live URL the slug will serve at
    registered : bool                                     # True on a successful registration
