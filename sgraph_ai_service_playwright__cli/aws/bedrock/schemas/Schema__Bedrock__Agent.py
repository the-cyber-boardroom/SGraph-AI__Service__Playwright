# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Bedrock__Agent
# An AgentCore agent definition as returned by list/get calls.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                               import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Agent_Arn   import Safe_Str__Bedrock__Agent_Arn
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id    import Safe_Str__Bedrock__Model_Id


class Schema__Bedrock__Agent(Type_Safe):
    agent_id         : str                                                            # AgentCore-assigned agent identifier
    agent_arn        : Safe_Str__Bedrock__Agent_Arn                                  # Full ARN
    agent_name       : str                                                            # Human-readable name (supplied at create)
    model_id         : Safe_Str__Bedrock__Model_Id                                   # Foundation model powering the agent
    status           : str                                                            # Agent status (CREATING, PREPARED, …)
    failure_reasons  : list                                                           # Non-empty when status=FAILED; strings from AWS
    instruction      : str                                                            # Agent instruction text (required before PrepareAgent)
    tools            : str                                                            # Comma-separated enabled tool names
    memory           : str                                                            # Memory scope (short / long / both / none)
    region           : str                                                            # AWS region
    capture_path     : str                                                            # Local folder for definition + session artefacts
