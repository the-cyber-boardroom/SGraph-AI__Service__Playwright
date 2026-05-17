# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: List__Slug
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug import Safe_Str__Slug


class List__Slug(Type_Safe__List):
    expected_type = Safe_Str__Slug
