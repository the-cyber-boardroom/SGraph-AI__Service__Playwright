# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: List__Bedrock__Chat__Message
# Typed list of conversation messages. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List           import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Message import Schema__Bedrock__Chat__Message


class List__Bedrock__Chat__Message(Type_Safe__List):
    expected_type = Schema__Bedrock__Chat__Message
