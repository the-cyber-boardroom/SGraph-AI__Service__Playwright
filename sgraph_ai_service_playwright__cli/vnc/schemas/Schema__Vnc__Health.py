# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vnc__Health
# Health snapshot returned by `sp vnc health <name>` and the matching FastAPI
# route. Three reachability flags + an optional flow count.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.primitives.Safe_Str__Vnc__Stack__Name    import Safe_Str__Vnc__Stack__Name


class Schema__Vnc__Health(Type_Safe):
    stack_name   : Safe_Str__Vnc__Stack__Name
    state        : Enum__Vnc__Stack__State = Enum__Vnc__Stack__State.UNKNOWN
    nginx_ok     : bool                    = False                                  # True iff nginx '/' returns 2xx (the operator UI / TLS terminator)
    mitmweb_ok   : bool                    = False                                  # True iff mitmweb /api/flows is reachable
    flow_count   : int                     = -1                                     # -1 ⇒ unreachable; 0 is a valid 'no flows yet'
    error        : Safe_Str__Text                                                   # Set when any probe failed; empty otherwise
