# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Schema__Vault_Publish__List__Response
# Vault keys are redacted in the listing response.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.List__Schema__Vault_Publish__Entry import List__Schema__Vault_Publish__Entry


class Schema__Vault_Publish__List__Response(Type_Safe):
    entries    : List__Schema__Vault_Publish__Entry = None
    total      : int                                = 0
    elapsed_ms : int                                = 0
