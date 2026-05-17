# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Bedrock__Tool__Session
# Typed list of AgentCore tool sessions. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List           import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Tool__Session import Schema__Bedrock__Tool__Session


class List__Schema__Bedrock__Tool__Session(Type_Safe__List):
    expected_type = Schema__Bedrock__Tool__Session
