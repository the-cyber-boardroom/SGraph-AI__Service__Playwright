# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Bedrock__Agent
# Typed list of AgentCore agent definitions. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List           import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Agent import Schema__Bedrock__Agent


class List__Schema__Bedrock__Agent(Type_Safe__List):
    expected_type = Schema__Bedrock__Agent
