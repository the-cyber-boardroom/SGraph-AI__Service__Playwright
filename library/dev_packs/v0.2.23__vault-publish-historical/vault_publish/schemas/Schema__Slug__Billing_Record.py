# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__Slug__Billing_Record
# PROPOSED — the billing record is owned by SG/Send (open question #2 in the dev
# pack). It already exists there because slug validation was first introduced
# for billing. This is the local representation: the only per-slug state, and
# the integrity anchor — it carries the owner binding and the signing key ref
# used to verify the provisioning manifest. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Safe_Str__Message               import Safe_Str__Message
from vault_publish.schemas.Safe_Str__Owner_Id              import Safe_Str__Owner_Id
from vault_publish.schemas.Safe_Str__Signing_Key_Ref       import Safe_Str__Signing_Key_Ref
from vault_publish.schemas.Safe_Str__Slug                  import Safe_Str__Slug


class Schema__Slug__Billing_Record(Type_Safe):
    slug                   : Safe_Str__Slug               # primary key
    owner_id               : Safe_Str__Owner_Id           # slug → owner binding
    signing_public_key_ref : Safe_Str__Signing_Key_Ref    # verifies the provisioning manifest
    created_at             : Safe_Str__Message            # ISO 8601 UTC — provisional type
    updated_at             : Safe_Str__Message            # ISO 8601 UTC — provisional type
