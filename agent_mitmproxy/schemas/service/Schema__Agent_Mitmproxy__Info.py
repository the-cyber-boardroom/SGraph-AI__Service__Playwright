# ═══════════════════════════════════════════════════════════════════════════════
# Agent Mitmproxy — Schema__Agent_Mitmproxy__Info (GET /health/info response)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                         import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Version              import Safe_Str__Version
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Display_Name    import Safe_Str__Display_Name


class Schema__Agent_Mitmproxy__Info(Type_Safe):
    service_name    : Safe_Str__Display_Name                                         # "agent-mitmproxy"
    service_version : Safe_Str__Version                                              # v0.1.32 — read from the baked /app/agent_mitmproxy/version
