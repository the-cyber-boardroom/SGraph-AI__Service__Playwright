# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__Status__Response
# Returned by GET /vault-publish/status/{slug}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Enum__Instance__State           import Enum__Instance__State
from vault_publish.schemas.Safe_Str__Instance__Id          import Safe_Str__Instance__Id
from vault_publish.schemas.Safe_Str__Message               import Safe_Str__Message
from vault_publish.schemas.Safe_Str__Slug                  import Safe_Str__Slug


class Schema__VaultPublish__Status__Response(Type_Safe):
    slug           : Safe_Str__Slug                       # the slug queried
    registered     : bool                                 # True if a billing record exists
    instance_state : Enum__Instance__State                # lifecycle state of the per-slug instance
    instance_id    : Safe_Str__Instance__Id               # EC2 instance id — empty if none allocated
    url            : Safe_Str__Message                    # the live URL
