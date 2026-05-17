# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Bedrock__Setup__Step
# Typed list of guided setup steps for `sg aws bedrock setup`.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List           import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Setup__Step import Schema__Bedrock__Setup__Step


class List__Schema__Bedrock__Setup__Step(Type_Safe__List):
    expected_type = Schema__Bedrock__Setup__Step
