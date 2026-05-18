# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: List__Schema__Setup__Issue
# Ordered list of setup issues. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue import Schema__Setup__Issue


class List__Schema__Setup__Issue(Type_Safe__List):
    expected_type = Schema__Setup__Issue
