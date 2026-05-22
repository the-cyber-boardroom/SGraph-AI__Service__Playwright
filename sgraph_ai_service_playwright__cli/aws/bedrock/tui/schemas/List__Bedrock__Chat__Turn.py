# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: List__Bedrock__Chat__Turn
# Typed list of per-turn cost records. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List           import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Turn import Schema__Bedrock__Chat__Turn


class List__Bedrock__Chat__Turn(Type_Safe__List):
    expected_type = Schema__Bedrock__Chat__Turn
