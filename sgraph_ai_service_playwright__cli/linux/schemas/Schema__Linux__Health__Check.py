# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Linux__Health__Check
# Input for a single health check probe. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.linux.primitives.Safe_Str__Linux__Stack__Name import Safe_Str__Linux__Stack__Name
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region   import Safe_Str__AWS__Region


class Schema__Linux__Health__Check(Type_Safe):
    stack_name   : Safe_Str__Linux__Stack__Name
    region       : Safe_Str__AWS__Region
    timeout_sec  : int = 300                                                        # Maximum seconds to wait for RUNNING state
    poll_sec     : int = 10                                                         # Seconds between state polls
