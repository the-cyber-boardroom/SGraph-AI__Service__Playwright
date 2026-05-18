# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: List__Schema__Setup__Action
# Ordered list of suggested remediation actions. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Action import Schema__Setup__Action


class List__Schema__Setup__Action(Type_Safe__List):
    expected_type = Schema__Setup__Action
