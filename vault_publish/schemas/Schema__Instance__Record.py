# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__Instance__Record
# The state Instance__Manager tracks for one per-slug vault instance. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Enum__Instance__State           import Enum__Instance__State
from vault_publish.schemas.Safe_Str__Instance__Id          import Safe_Str__Instance__Id
from vault_publish.schemas.Safe_Str__Slug                  import Safe_Str__Slug


class Schema__Instance__Record(Type_Safe):
    slug             : Safe_Str__Slug                     # the slug this instance serves
    instance_id      : Safe_Str__Instance__Id             # EC2 instance id — empty until allocated
    state            : Enum__Instance__State              # lifecycle state
    idle_timer_armed : bool                               # True once the idle-shutdown timer is armed
