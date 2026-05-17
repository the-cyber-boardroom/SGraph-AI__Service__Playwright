# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__Provisioning__Plan
# The ordered, allowlisted plan Manifest__Interpreter produces from a verified
# manifest. This — never the raw manifest — is what the control-plane acts on.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.List__Provisioning__Step        import List__Provisioning__Step


class Schema__Provisioning__Plan(Type_Safe):
    steps : List__Provisioning__Step                       # executed top-down by the control-plane
