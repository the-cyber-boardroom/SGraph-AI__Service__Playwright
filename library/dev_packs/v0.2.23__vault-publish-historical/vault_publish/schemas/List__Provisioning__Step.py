# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — List__Provisioning__Step
# Ordered list of provisioning steps produced by Manifest__Interpreter.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from vault_publish.schemas.Schema__Provisioning__Step                import Schema__Provisioning__Step


class List__Provisioning__Step(Type_Safe__List):
    expected_type = Schema__Provisioning__Step
