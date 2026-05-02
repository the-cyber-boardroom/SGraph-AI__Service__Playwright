# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Vault__Write__Receipt
# Ordered list of vault write receipts for GET /vault/plugin/{plugin_id}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List                  import Type_Safe__List

from sgraph_ai_service_playwright__cli.vault.schemas.Schema__Vault__Write__Receipt      import Schema__Vault__Write__Receipt


class List__Schema__Vault__Write__Receipt(Type_Safe__List):
    expected_type = Schema__Vault__Write__Receipt
