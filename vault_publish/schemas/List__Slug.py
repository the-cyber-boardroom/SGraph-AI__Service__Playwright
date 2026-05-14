# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — List__Slug
# Ordered list of registered slugs.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from vault_publish.schemas.Safe_Str__Slug                            import Safe_Str__Slug


class List__Slug(Type_Safe__List):
    expected_type = Safe_Str__Slug
