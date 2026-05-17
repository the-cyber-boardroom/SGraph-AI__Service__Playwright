# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__Manifest__Signature
# A detached signature over a provisioning manifest. Manifest__Verifier checks
# it against the signing key referenced by the slug's billing record.
# The concrete signing scheme is open question #4, owned by SG/Send.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Safe_Str__Message               import Safe_Str__Message
from vault_publish.schemas.Safe_Str__Signature__Value      import Safe_Str__Signature__Value
from vault_publish.schemas.Safe_Str__Signing_Key_Ref       import Safe_Str__Signing_Key_Ref


class Schema__Manifest__Signature(Type_Safe):
    algorithm       : Safe_Str__Message                    # signing algorithm identifier
    value           : Safe_Str__Signature__Value           # the signature itself
    signing_key_ref : Safe_Str__Signing_Key_Ref            # which key signed it
