# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: List__Bedrock__Chat__Document
# Typed list of attached documents. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Document import Schema__Bedrock__Chat__Document


class List__Bedrock__Chat__Document(Type_Safe__List):
    expected_type = Schema__Bedrock__Chat__Document
