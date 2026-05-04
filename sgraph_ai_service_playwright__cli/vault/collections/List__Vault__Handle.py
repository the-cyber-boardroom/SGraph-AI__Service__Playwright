# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Vault__Handle
# Ordered list of vault handle slugs declared by a plugin manifest.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List                  import Type_Safe__List

from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__Vault__Handle         import Safe_Str__Vault__Handle


class List__Vault__Handle(Type_Safe__List):
    expected_type = Safe_Str__Vault__Handle
