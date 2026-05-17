# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Bedrock__Tool__Session
# An AgentCore inline-tool session (browser or code-interpreter).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                               import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Tool__Type   import Enum__Bedrock__Tool__Type
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Session_Id import Safe_Str__Bedrock__Session_Id


class Schema__Bedrock__Tool__Session(Type_Safe):
    session_id   : Safe_Str__Bedrock__Session_Id                                     # AgentCore-assigned session identifier
    tool_type    : Enum__Bedrock__Tool__Type                                          # browser or code-interpreter
    status       : str                                                                # Session status (STARTING, ACTIVE, STOPPED, …)
    language     : str                                                                # Only for code-interpreter — python/javascript/typescript
    region       : str                                                                # AWS region
    capture_path : str                                                                # Local folder for session artefacts
