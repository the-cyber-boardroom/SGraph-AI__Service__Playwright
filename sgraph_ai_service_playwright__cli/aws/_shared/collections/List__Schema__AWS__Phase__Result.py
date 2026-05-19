# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/_shared — List__Schema__AWS__Phase__Result
# Typed list of phase-timer records.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Phase__Result import Schema__AWS__Phase__Result


class List__Schema__AWS__Phase__Result(Type_Safe__List):
    expected_type = Schema__AWS__Phase__Result
