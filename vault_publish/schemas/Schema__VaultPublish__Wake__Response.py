# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__VaultPublish__Wake__Response
# Returned by POST /vault-publish/wake. 'warming' True means the caller should
# serve the auto-refreshing warming page; the instance is not yet healthy.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Enum__Instance__State           import Enum__Instance__State
from vault_publish.schemas.Enum__Wake__Outcome             import Enum__Wake__Outcome
from vault_publish.schemas.Safe_Str__Instance__Id          import Safe_Str__Instance__Id
from vault_publish.schemas.Safe_Str__Message               import Safe_Str__Message
from vault_publish.schemas.Safe_Str__Slug                  import Safe_Str__Slug


class Schema__VaultPublish__Wake__Response(Type_Safe):
    slug           : Safe_Str__Slug                       # the slug woken — empty if the slug was invalid
    outcome        : Enum__Wake__Outcome                  # what the wake sequence did
    instance_state : Enum__Instance__State                # state after the wake attempt
    instance_id    : Safe_Str__Instance__Id               # EC2 instance id — empty if none allocated
    warming        : bool                                 # True → serve the warming page
    detail         : Safe_Str__Message                    # human-readable explanation
