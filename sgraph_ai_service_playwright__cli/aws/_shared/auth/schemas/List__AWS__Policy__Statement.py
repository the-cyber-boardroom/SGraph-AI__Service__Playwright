# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: List__AWS__Policy__Statement
# Typed list of Schema__AWS__Policy__Statement. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws._shared.auth.schemas.Schema__AWS__Policy__Statement import Schema__AWS__Policy__Statement


class List__AWS__Policy__Statement(Type_Safe__List):
    expected_type = Schema__AWS__Policy__Statement
